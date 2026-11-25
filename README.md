# Website Technologies Scraper

Veridion Internship Challenge: identify website technologies from HTTP headers,
cookies and HTML. Built with Python 3.10+, HTTPX, Beautiful Soup and lxml.

The scanner includes 47 editable technology signatures. Each detection records
which rules matched. It fetches the supplied page rather than crawling the whole
website, and it does not execute JavaScript.

**Dataset scope:** this repository contains a 10-domain sample and its real output.
The assessment's 200-domain list was not supplied. The observations below describe
only those 10 domains; a full assessment run is still needed before submission.

## Run locally

```bash
python -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

On Linux or macOS, use `source .venv/bin/activate` instead.

```bash
python -m pip install -r requirements.txt
python main.py domains.txt
```

This writes `output.json` and `output.csv` in the current directory, replacing
existing files. Both sample outputs are tracked in the repository.

```bash
python main.py domains.txt --concurrency 15 --output-dir outputs
python main.py domains.txt --format json --timeout 10 --retries 1
python main.py domains.txt --no-http-fallback --domain-timeout 60
python -m unittest discover -s tests -v
```

Input is a UTF-8 file with one domain or HTTP(S) URL per line. Blank lines and
lines starting with `#` are ignored. Bare domains start with HTTPS. Paths and
queries are preserved, fragments removed, and international hostnames converted
to IDNA. Duplicate inputs remain separate rows in input order. Invalid entries
produce error records without stopping other domains.

| Option | Default | Purpose |
| --- | --- | --- |
| `--format` | `both` | `json`, `csv` or `both` |
| `--output-dir` | `.` | Output directory |
| `--concurrency` | `20` | Active domain fetch jobs |
| `--timeout` | `15` | Seconds per HTTP connect/read/write/pool operation |
| `--domain-timeout` | `90` | Total fetch budget, including retries |
| `--retries` | `2` | Additional attempts per protocol |
| `--max-bytes` | `2000000` | Retained decompressed body bytes |
| `--no-http-fallback` | off | Disable HTTPS-to-HTTP fallback |
| `--verbose` | off | Include per-domain debug logging |

The summary reports processed domains, successful responses, failures by type
and the most common detections. Exit code `0` means the batch was exported, not
that every domain succeeded. File/configuration failures return `1`, invalid CLI
arguments return `2`, and interruption returns `130`.

## Layout and architecture

```text
main.py                 CLI, batch orchestration and summary
fetcher.py              URL handling, HTTP requests, retries and limits
analyzer.py             Signal extraction and rule matching
signatures.py           Technology names, categories and detection rules
models.py               Fetch, detection and output records
exporter.py             JSON and CSV writers
requirements.txt        Pinned direct runtime dependencies
domains.txt             10-domain sample
output.json             Sample results with matching evidence
output.csv              Sample results in tabular form
tests/test_scraper.py   Offline regression tests
```

HTTP fetching is asynchronous because network waits dominate this workload. A
semaphore limits active domain jobs, including time spent retrying. Each domain
has its own HTTP client and cookie jar, with connection reuse for redirects and
retries. This keeps duplicate inputs from sharing cookies, at the cost of some
connection setup overhead. A semaphore is a concurrency limit, not a per-host
requests-per-second limit.

HTML parsing runs synchronously with Beautiful Soup and lxml. For a few hundred
bounded pages this is simple enough; profiling should come before adding parser
processes. The batch uses `asyncio.gather`, so results preserve input order.

Headless browsers would reveal JavaScript-injected tags and network calls, but
would add installation cost, memory use and rendering delays to every request.
HTTP first is a reasonable compromise. A later browser pass should target pages
where rendering is likely to add useful evidence.

### Detection rules

Rules match header values, cookie names, named meta content, script URLs, inline
scripts, stylesheet URLs and CSS selectors. Asset URLs resolve against the final
page URL and its `<base>` tag when present. Regexes are case-insensitive and
compiled once. Invalid regexes, selectors or rule sources fail at startup.

Add entries to `SIGNATURES` using this structure:

```python
{
    "name": "ExampleCMS",
    "category": "CMS",
    "rules": [
        ("meta", "generator", r"^ExampleCMS(?:\s|$)"),
        ("script_src", "", r"^(?:https?:)?//cdn\.examplecms\.com/"),
        ("selector", "html[data-examplecms-site]", ""),
    ],
}
```

Each tuple is `(source, key, pattern)`. For headers and meta tags, `key` selects
the field; an empty key searches all fields of that source. For selectors, `key`
is the CSS selector and the pattern is unused. Other sources use an empty key.
Any matching rule detects that technology. Use distinctive signals because there
is no weighting or confidence threshold. Add positive and negative fixtures when
changing a rule.

### Output

Both formats contain the original input, normalized URL, final response URL,
HTTP status, technologies, errors and notes. JSON includes category and matching
rules for each technology. CSV has one row per input with semicolon-separated
technology names, categories and notes; detailed evidence stays in JSON.

Cookie values and raw HTML are not exported. A failed response may still identify
a server or CDN. A transport failure after receiving headers can retain the last
status; the error field determines whether the fetch succeeded. A missing response
has a null JSON status or an empty CSV cell. No match means insufficient evidence,
not that the website uses no technology.

## Observations from the included run

The included outputs were generated on **25 November 2026**, using Python 3.12.10:

```bash
python main.py domains.txt --concurrency 5 --timeout 10 --domain-timeout 30 --retries 1
```

| Observation | Result |
| --- | --- |
| Inputs | 10 |
| Successful final HTTP responses | 10, all HTTP 200 |
| Fetch failures | 0 |
| Domains with at least one detection | 9 |
| Cloudflare detections | 4 |
| Google Tag Manager detections | 3 |
| nginx detections | 3 |
| WordPress detections | 2 |
| Responses truncated at the body limit | 1: wix.com |

WooCommerce's site produced six detections, including WooCommerce, WordPress and
jQuery. Drupal's site returned HTTP 200 but matched no rules. Shopify's site
matched Cloudflare only, and Ghost's matched Netlify only. A vendor's marketing
site is not proof that it exposes the vendor's product signatures.

Stripe redirected to `/en-ro` from this execution environment and exposed Next.js
and nginx signals, but no Stripe payment SDK signature. The locale-dependent
redirect illustrates why crawl location can affect results. Wix exceeded the
2 MB body limit, so its detections cover only the retained HTML.

These are observations, not a precision/recall benchmark: there is no independently
labeled ground truth. No rate-limit, TLS or timeout failures occurred in this
sample; those paths are covered by offline tests rather than claimed as live
findings. The small vendor-heavy list cannot represent the missing 200-domain
assessment dataset. Replace `domains.txt` with that list, rerun the same command
and update this section before presenting full-dataset conclusions.

## Debate 1: Implementation issues and fixes

**Network failures and broken TLS.** Requests have operation timeouts and a total
domain budget. Network failures and HTTP 429/500/502/503/504 are retried with
backoff and jitter. Retry-After supports seconds and dates, capped at 30 seconds
for this batch tool. TLS verification remains enabled. Failed HTTPS connections
can fall back to HTTP, with the reason recorded in notes; this also applies to
explicit HTTPS input. `--no-http-fallback` disables that downgrade. Redirect loops
stop after ten redirects. The total budget excludes semaphore waiting and parsing.

**403s and anti-bot responses.** A 403 or 404 is recorded without retries or HTTP
downgrade. Its headers and HTML can still identify an edge provider. A challenge
can also return HTTP 200, so status alone cannot prove that the application page
was reached. The User-Agent improves compatibility but does not bypass protection.

**JavaScript-rendered pages.** Sparse visible text with script tags adds a possible
SPA note. This is a triage hint, not a reliable classifier. Client-side injected
analytics, consent-gated integrations and checkout-only payment SDKs can be missed.
Modern bundled React or Vue may leave no stable server-rendered signature. The
scanner does not infer React merely because it detects Next.js.

**False positives.** Matching is scoped to specific HTML fields rather than
searching visible prose for product names. Vendor URL patterns use hostname
boundaries. Still, unused inline integrations and reused cookie names can mislead
the detector. Fastly's cache naming pattern is weaker than a unique vendor header.
Evidence makes those decisions reviewable. Precision should be measured on labeled
positive and negative examples before broadening a rule.

**Large and non-HTML responses.** Explicitly non-HTML bodies are skipped. HTML is
streamed and truncated at the configured limit, with a note. This bounds retained
input, not every decompressor or parser allocation. Missing late-page signals is
an accepted trade-off. Redirect cookies contribute names to detection, while
header rules inspect only the last received response.

**Regression checks.** Nine offline tests cover URL normalization, positive and
negative matches, redirects, cookie isolation, retries, TLS fallback, redirect
loops, body limits, concurrency, total timeouts and JSON/CSV round-tripping. All
pass in the packaged revision. Direct runtime dependencies are pinned; transitive
dependencies are resolved by pip rather than fully locked.

## Debate 2: Millions of domains in 1–2 months

Ten million domains over 30 days require about 3.9 completed domains per second
before retries. One hundred million require about 38.6 per second. At an average
500 KB per response, ten million domains produce roughly 5 TB of uncompressed
payloads. Measure latency, response sizes and browser share on a representative
sample before choosing worker counts.

I would first replace the in-memory batch with a durable RabbitMQ or Kafka queue.
Messages would carry a normalized URL, crawl window and rules version. Workers
would acknowledge after storing results. Since delivery can repeat, writes need
an idempotency key and retries need a dead-letter path.

Stateless HTTP worker containers would consume bounded batches. Host-level limits
must be shared across replicas, using partitioned scheduling or Redis token
buckets. Redirect targets need the same treatment. Delayed retries should honor
the full Retry-After interval instead of sleeping inside workers. Scheduling should
also account for robots policies, host cooldowns and retry amplification.

A separate, smaller browser queue would handle selected sparse or low-evidence
pages. Browser jobs need navigation, execution and memory budgets. Repeated
challenge pages should remain unresolved instead of consuming unlimited retries.

Compressed snapshots would go to S3, with retention limits and sensitive-header
filtering. Structured observations would go to date- and rules-version-partitioned
Parquet. An operational database would track crawl state and latest results.
Snapshot references let new rules run against old HTML without another network
request.

The first two weeks would establish a labeled sample, throughput measurements and
queue/storage contracts. Weeks three and four would add workers, idempotent writes,
host scheduling and monitoring. The remaining month would cover the selective
browser pass, load tests and rule-quality checks. Queue lag, tail latency, errors
by host, bytes fetched and cost per useful result would guide capacity changes.

## Debate 3: Discovering new technologies

Discovery should run offline against collected observations, separately from the
deterministic matcher.

Start with unmatched script hosts, normalized asset paths, custom header names,
meta generators and DOM fingerprints. Remove cache-busters, version fragments and
identifiers. Count distinct registrable domains so one large website does not
dominate the results.

Cluster features that repeatedly appear together, using sparse vectors or MinHash
for structural similarity. Rank clusters by adoption and growth. Compare them
with known signatures to distinguish a new product from a vendor changing its CDN.

For promising clusters, inspect representative samples and vendor documentation.
An LLM or NLP classifier can propose product names, categories and regexes from
sanitized feature summaries. Those proposals need review: popular scripts can be
advertising networks or shared infrastructure rather than application frameworks.
Fetched content is input data, not instructions, and generated rules should never
be executed as arbitrary code.

Each candidate should include examples, negative fixtures and regex performance
checks. Test it against a held-out labeled corpus, deploy to a small sample, then
promote the versioned rule and backfill stored snapshots. Monitor changes in
coverage and false positives so stale signatures can be corrected or removed.
