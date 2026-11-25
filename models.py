from dataclasses import dataclass, field


@dataclass
class FetchResult:
    domain: str
    url: str = ""
    final_url: str = ""
    status: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    cookies: list[str] = field(default_factory=list)
    html: str = ""
    error: str | None = None
    error_type: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class Detection:
    name: str
    category: str
    evidence: list[str]


@dataclass
class ScanResult:
    domain: str
    url: str
    final_url: str
    status: int | None
    technologies: list[Detection]
    error: str | None
    error_type: str | None
    notes: list[str]
