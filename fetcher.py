import asyncio
import random
import ssl
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

import httpx

from models import FetchResult

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
RETRY_STATUSES = {429, 500, 502, 503, 504}


def normalize_url(value: str) -> str:
    value = value.strip()
    if any(c.isspace() for c in value):
        raise ValueError("URLs cannot contain whitespace")
    if value.startswith("//"):
        value = "https:" + value
    elif "://" not in value:
        value = "https://" + value
    parts = urlsplit(value)
    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported")
    if not parts.hostname or parts.username is not None or parts.password is not None:
        raise ValueError("A hostname without embedded credentials is required")
    port = parts.port
    host = parts.hostname.encode("idna").decode("ascii").lower()
    if any(c in host for c in "\\%"):
        raise ValueError("Invalid hostname")
    authority = f"[{host}]" if ":" in host else host
    if port is not None:
        authority += f":{port}"
    return urlunsplit(
        (parts.scheme.lower(), authority, parts.path or "/", parts.query, "")
    )


def error_kind(exc: Exception) -> str:
    cause = exc
    while cause is not None:
        if isinstance(cause, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(cause):
            return "ssl_error"
        cause = cause.__cause__
    if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
        return "timeout"
    if isinstance(exc, httpx.TooManyRedirects):
        return "redirect_error"
    return "network_error"


def retry_delay(value: str | None, attempt: int) -> float:
    if value:
        try:
            return min(30.0, max(0.0, float(value)))
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                return min(
                    30.0, max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
                )
            except (ValueError, TypeError, OverflowError):
                pass
    return min(30.0, 0.5 * 2**attempt + random.uniform(0, 0.25))


class Fetcher:
    def __init__(
        self,
        concurrency: int = 20,
        timeout: float = 15,
        retries: int = 2,
        domain_timeout: float = 90,
        max_bytes: int = 2_000_000,
        http_fallback: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if min(concurrency, timeout, domain_timeout, max_bytes) <= 0 or retries < 0:
            raise ValueError("Limits must be positive and retries nonnegative")
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.retries = retries
        self.domain_timeout = domain_timeout
        self.max_bytes = max_bytes
        self.http_fallback = http_fallback
        self.transport = transport

    async def fetch(self, domain: str) -> FetchResult:
        result = FetchResult(domain=domain)
        try:
            result.url = normalize_url(domain)
        except (ValueError, UnicodeError) as exc:
            result.error, result.error_type = str(exc), "invalid_input"
            return result
        async with self.semaphore:
            try:
                await asyncio.wait_for(self._fetch(result), self.domain_timeout)
            except asyncio.TimeoutError:
                result.error = f"Domain budget exceeded ({self.domain_timeout:g}s)"
                result.error_type = "timeout"
        return result

    async def _fetch(self, result: FetchResult) -> None:
        async with httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
            },
            timeout=self.timeout,
            follow_redirects=True,
            max_redirects=10,
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
            transport=self.transport,
        ) as client:
            url = result.url
            while True:
                for attempt in range(self.retries + 1):
                    try:
                        async with client.stream("GET", url) as response:
                            result.final_url = str(response.url)
                            result.status = response.status_code
                            result.headers = dict(response.headers)
                            result.cookies = sorted(
                                {c.name for c in client.cookies.jar}
                            )
                            result.html = ""
                            result.error = result.error_type = None
                            if (
                                response.status_code in RETRY_STATUSES
                                and attempt < self.retries
                            ):
                                delay = retry_delay(
                                    response.headers.get("retry-after"), attempt
                                )
                                result.notes.append(
                                    f"Retrying HTTP {response.status_code} (attempt {attempt + 1})"
                                )
                            else:
                                await self._read_body(response, result)
                                if not 200 <= response.status_code < 300:
                                    result.error = f"HTTP {response.status_code}"
                                    result.error_type = f"http_{response.status_code}"
                                if response.history:
                                    result.notes.append(
                                        f"Followed {len(response.history)} redirect(s)"
                                    )
                                return
                        await asyncio.sleep(delay)
                    except (httpx.RequestError, httpx.InvalidURL) as exc:
                        result.error = f"{type(exc).__name__}: {exc}"
                        result.error_type = error_kind(exc)
                        if result.error_type in {"ssl_error", "redirect_error"}:
                            break
                        if attempt < self.retries:
                            result.notes.append(
                                f"Retrying {result.error_type} (attempt {attempt + 1})"
                            )
                            await asyncio.sleep(retry_delay(None, attempt))
                if (
                    self.http_fallback
                    and urlsplit(url).scheme == "https"
                    and result.error_type in {"ssl_error", "timeout", "network_error"}
                ):
                    result.notes.append(f"HTTPS failed ({result.error}); trying HTTP")
                    url = "http:" + url[len("https:") :]
                    continue
                return

    async def _read_body(self, response: httpx.Response, result: FetchResult) -> None:
        content_type = response.headers.get("content-type", "").lower()
        if content_type and not any(
            t in content_type for t in ("text/html", "application/xhtml+xml")
        ):
            result.notes.append(f"Skipped non-HTML body: {content_type}")
            return
        body = bytearray()
        async for chunk in response.aiter_bytes(chunk_size=65536):
            remaining = self.max_bytes - len(body)
            body.extend(chunk[:remaining])
            if len(chunk) > remaining:
                result.notes.append(f"HTML truncated at {self.max_bytes} bytes")
                break
        encoding = response.encoding or "utf-8"
        try:
            result.html = body.decode(encoding, errors="replace")
        except LookupError:
            result.html = body.decode("utf-8", errors="replace")
            result.notes.append("Unknown character encoding; decoded as UTF-8")
