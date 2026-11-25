import argparse
import asyncio
import logging
from collections import Counter
from pathlib import Path

from analyzer import Analyzer
from exporter import export_results
from fetcher import Fetcher
from models import ScanResult

logger = logging.getLogger(__name__)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return number


async def scan(
    domains: list[str], fetcher: Fetcher, analyzer: Analyzer
) -> list[ScanResult]:
    async def scan_one(domain: str) -> ScanResult:
        page = await fetcher.fetch(domain)
        try:
            technologies = analyzer.analyze(page)
        except Exception as exc:
            logger.exception("Analysis failed for %s", domain)
            technologies = []
            page.notes.append(f"Analysis failed: {type(exc).__name__}: {exc}")
            if not page.error:
                page.error, page.error_type = str(exc), "analysis_error"
        logger.debug(
            "%s: HTTP %s, %d technologies%s",
            domain,
            page.status,
            len(technologies),
            f", {page.error_type}" if page.error else "",
        )
        return ScanResult(
            page.domain,
            page.url,
            page.final_url,
            page.status,
            technologies,
            page.error,
            page.error_type,
            page.notes,
        )

    return await asyncio.gather(*(scan_one(domain) for domain in domains))


def log_summary(results: list[ScanResult]) -> None:
    errors = Counter(r.error_type or "unknown" for r in results if r.error)
    successes = sum(
        r.error is None and r.status is not None and 200 <= r.status < 300
        for r in results
    )
    technologies = Counter(t.name for r in results for t in r.technologies)
    logger.info(
        "Summary: total=%d successful=%d failed=%d",
        len(results),
        successes,
        len(results) - successes,
    )
    logger.info("Error breakdown: %s", dict(errors) or "none")
    logger.info("Top technologies: %s", technologies.most_common(10) or "none")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Identify technologies from website HTTP responses and HTML."
    )
    parser.add_argument(
        "input", type=Path, help="UTF-8 file: one domain or URL per line"
    )
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--concurrency", type=positive_int, default=20)
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=15,
        help="HTTP operation timeout in seconds",
    )
    parser.add_argument(
        "--domain-timeout",
        type=positive_int,
        default=90,
        help="Total fetch budget, excluding semaphore wait",
    )
    parser.add_argument(
        "--retries",
        type=nonnegative_int,
        default=2,
        help="Additional tries per protocol",
    )
    parser.add_argument("--max-bytes", type=positive_int, default=2_000_000)
    parser.add_argument("--no-http-fallback", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        domains = [
            line.strip()
            for line in args.input.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not domains:
            parser.error("input file has no domains")
        analyzer = Analyzer()
        fetcher = Fetcher(
            concurrency=args.concurrency,
            timeout=args.timeout,
            retries=args.retries,
            domain_timeout=args.domain_timeout,
            max_bytes=args.max_bytes,
            http_fallback=not args.no_http_fallback,
        )
        results = asyncio.run(scan(domains, fetcher, analyzer))
        paths = export_results(results, args.output_dir, args.format)
    except (OSError, ValueError) as exc:
        logger.error("Cannot complete batch: %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted")
        return 130
    log_summary(results)
    for path in paths:
        logger.info("Wrote %s", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
