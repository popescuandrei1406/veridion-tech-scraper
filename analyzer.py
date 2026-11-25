import re
from urllib.parse import urljoin

import soupsieve
from bs4 import BeautifulSoup

from models import Detection, FetchResult
from signatures import SIGNATURES


class Analyzer:
    def __init__(self, signatures=None):
        self.signatures = []
        names = set()
        for technology in SIGNATURES if signatures is None else signatures:
            name = technology["name"]
            if name in names or not technology["rules"]:
                raise ValueError(f"Duplicate name or empty rules: {name}")
            names.add(name)
            rules = []
            for source, key, pattern in technology["rules"]:
                if source not in {
                    "header",
                    "cookie",
                    "meta",
                    "script_src",
                    "inline_script",
                    "stylesheet",
                    "selector",
                }:
                    raise ValueError(f"Unknown source {source} in {name}")
                compiled = (
                    soupsieve.compile(key)
                    if source == "selector"
                    else re.compile(pattern, re.I)
                )
                rules.append(
                    (
                        source,
                        key.lower() if source in {"header", "meta"} else key,
                        compiled,
                    )
                )
            self.signatures.append((name, technology["category"], rules))

    def analyze(self, page: FetchResult) -> list[Detection]:
        soup = BeautifulSoup(page.html, "lxml")
        base = page.final_url or page.url
        base_tag = soup.find("base", href=True)
        if base_tag:
            base = urljoin(base, base_tag["href"])
        signals = {
            "header": [(name.lower(), value) for name, value in page.headers.items()],
            "cookie": [("", name) for name in page.cookies],
            "meta": [],
            "script_src": [],
            "inline_script": [],
            "stylesheet": [],
        }
        for tag in soup.find_all("meta"):
            signals["meta"].append(
                (
                    str(tag.get("name", tag.get("property", ""))).lower(),
                    str(tag.get("content", "")),
                )
            )
        for tag in soup.find_all("script"):
            if tag.get("src"):
                signals["script_src"].append(("", urljoin(base, tag["src"])))
            else:
                signals["inline_script"].append(("", tag.string or tag.get_text()))
        for tag in soup.find_all("link", href=True):
            if "stylesheet" in [str(rel).lower() for rel in tag.get("rel", [])]:
                signals["stylesheet"].append(("", urljoin(base, tag["href"])))
        detections = []
        for name, category, rules in self.signatures:
            evidence = []
            for source, key, compiled in rules:
                if source == "selector":
                    if compiled.select_one(soup) is not None:
                        evidence.append(f"selector: {key}")
                elif any(
                    (not key or key == field) and compiled.search(value)
                    for field, value in signals[source]
                ):
                    evidence.append(
                        f"{source}{':' + key if key else ''}: /{compiled.pattern}/"
                    )
            if evidence:
                detections.append(Detection(name, category, evidence))
        if (
            page.html
            and len(soup.get_text(" ", strip=True)) < 100
            and soup.find("script")
        ):
            page.notes.append(
                "Little visible text: possible SPA; browser rendering may improve coverage"
            )
        return sorted(detections, key=lambda detection: detection.name.lower())
