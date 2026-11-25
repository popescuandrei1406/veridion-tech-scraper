import asyncio
import csv
import json
import tempfile
import unittest
from pathlib import Path

import httpx

from analyzer import Analyzer
from exporter import export_results
from fetcher import Fetcher, normalize_url
from main import scan
from models import FetchResult


class DetectionTests(unittest.TestCase):
    def test_scoped_evidence_and_false_positive_controls(self):
        page = FetchResult(
            "example.com",
            url="https://example.com/",
            headers={"Server": "nginx"},
            cookies=["PHPSESSID"],
            html="""<html data-wf-site="123"><head>
            <meta name="generator" content="WordPress 6.7">
            <script src="/wp-content/plugins/woocommerce/app.js"></script>
            <script src="https://js.stripe.com/v3/"></script>
            <script>gtag('config', 'G-TEST');</script>
            </head><body ng-version="18">React Vue Shopify
            <link rel="stylesheet" href="/bootstrap.min.css">
            <script src="https://evil.example/js.stripe.com/fake.js"></script></body></html>""",
        )
        found = {t.name: t for t in Analyzer().analyze(page)}
        self.assertTrue(
            {
                "nginx",
                "PHP",
                "WordPress",
                "WooCommerce",
                "Stripe",
                "Google Analytics",
                "Webflow",
                "Angular",
                "Bootstrap",
            }
            <= found.keys()
        )
        self.assertFalse(
            {"React", "Vue.js", "Shopify", "Google Tag Manager"} & found.keys()
        )
        self.assertTrue(all(t.evidence for t in found.values()))
        fake = FetchResult(
            "example.com",
            html='<p>Stripe WordPress</p><script src="https://js.stripe.com.evil.test/v3/"></script>',
        )
        self.assertEqual(Analyzer().analyze(fake), [])

    def test_normalization(self):
        self.assertEqual(
            normalize_url(" Example.COM/store?q=1#top "),
            "https://example.com/store?q=1",
        )
        self.assertEqual(normalize_url("//example.com"), "https://example.com/")
        self.assertEqual(normalize_url("http://[::1]:8000"), "http://[::1]:8000/")
        for invalid in [
            "",
            "ftp://example.com",
            "a b",
            "https://user:pass@example.com",
            "example.com:99999",
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                normalize_url(invalid)


class FetchTests(unittest.IsolatedAsyncioTestCase):
    async def test_redirect_cookie_and_export_roundtrip(self):
        def handler(request):
            if request.url.path == "/":
                return httpx.Response(
                    302,
                    headers={
                        "location": "/shop",
                        "set-cookie": "_shopify_y=secret; Path=/",
                    },
                )
            return httpx.Response(
                200, headers={"content-type": "text/html"}, text="<h1>Store</h1>"
            )

        results = await scan(
            ["example.com"], Fetcher(transport=httpx.MockTransport(handler)), Analyzer()
        )
        self.assertEqual(results[0].final_url, "https://example.com/shop")
        self.assertIn("Shopify", [t.name for t in results[0].technologies])
        with tempfile.TemporaryDirectory() as directory:
            export_results(results, Path(directory))
            text = (Path(directory) / "output.json").read_text(encoding="utf-8")
            self.assertNotIn("secret", text)
            self.assertEqual(json.loads(text)[0]["status"], 200)
            with (Path(directory) / "output.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                self.assertEqual(
                    list(csv.DictReader(handle))[0]["technologies"], "Shopify"
                )

    async def test_retry_and_no_downgrade_on_forbidden(self):
        calls = []

        def handler(request):
            calls.append(str(request.url))
            return httpx.Response(
                429 if len(calls) == 1 else 403,
                headers={"retry-after": "0", "cf-ray": "abc"},
                text="Blocked",
            )

        result = await Fetcher(transport=httpx.MockTransport(handler)).fetch(
            "example.com"
        )
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(url.startswith("https:") for url in calls))
        self.assertEqual(result.error_type, "http_403")
        self.assertEqual(Analyzer().analyze(result)[0].name, "Cloudflare")

    async def test_ssl_fallback_and_opt_out(self):
        def handler(request):
            if request.url.scheme == "https":
                raise httpx.ConnectError("CERTIFICATE_VERIFY_FAILED", request=request)
            return httpx.Response(200, text="<p>OK</p>")

        result = await Fetcher(transport=httpx.MockTransport(handler)).fetch(
            "example.com"
        )
        self.assertIsNone(result.error)
        self.assertEqual(result.final_url, "http://example.com/")
        self.assertTrue(any("HTTPS failed" in note for note in result.notes))
        result = await Fetcher(
            http_fallback=False, transport=httpx.MockTransport(handler)
        ).fetch("example.com")
        self.assertEqual(result.error_type, "ssl_error")

    async def test_redirect_loop(self):
        result = await Fetcher(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(302, headers={"location": "/loop"})
            )
        ).fetch("example.com")
        self.assertEqual(result.error_type, "redirect_error")

    async def test_body_cap_and_non_html(self):
        result = await Fetcher(
            max_bytes=20,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, headers={"content-type": "text/html"}, text="x" * 100
                )
            ),
        ).fetch("example.com")
        self.assertEqual(len(result.html), 20)
        self.assertTrue(any("truncated" in note for note in result.notes))
        result = await Fetcher(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, headers={"content-type": "application/pdf"}, content=b"PDF"
                )
            )
        ).fetch("example.com")
        self.assertEqual(result.html, "")
        self.assertTrue(result.notes)

    async def test_concurrency_and_cookie_isolation(self):
        active = peak = 0

        async def handler(request):
            nonlocal active, peak
            self.assertNotIn("cookie", request.headers)
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return httpx.Response(200, headers={"set-cookie": "session=value; Path=/"})

        fetcher = Fetcher(concurrency=2, transport=httpx.MockTransport(handler))
        await asyncio.gather(*(fetcher.fetch("example.com") for _ in range(6)))
        self.assertEqual(peak, 2)

    async def test_total_timeout(self):
        async def handler(request):
            await asyncio.sleep(1)
            return httpx.Response(200)

        result = await Fetcher(
            domain_timeout=0.01, transport=httpx.MockTransport(handler)
        ).fetch("example.com")
        self.assertEqual(result.error_type, "timeout")


if __name__ == "__main__":
    unittest.main()
