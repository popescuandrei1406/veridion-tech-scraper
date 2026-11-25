import csv
import json
from dataclasses import asdict
from pathlib import Path

from models import ScanResult


def export_results(
    results: list[ScanResult], output_dir: Path, format: str = "both"
) -> list[Path]:
    if format not in {"json", "csv", "both"}:
        raise ValueError(f"Unknown format: {format}")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    if format in {"json", "both"}:
        path = output_dir / "output.json"
        path.write_text(
            json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        paths.append(path)
    if format in {"csv", "both"}:
        path = output_dir / "output.csv"
        fields = [
            "domain",
            "url",
            "final_url",
            "status",
            "technologies",
            "categories",
            "error",
            "error_type",
            "notes",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for result in results:
                row = asdict(result)
                row["technologies"] = "; ".join(t.name for t in result.technologies)
                row["categories"] = "; ".join(
                    sorted({t.category for t in result.technologies})
                )
                row["notes"] = "; ".join(result.notes)
                writer.writerow(row)
        paths.append(path)
    return paths
