from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass(frozen=True, slots=True)
class MetadataExportConfig:
    metadata_id: str
    include_sources: bool = True
    include_keywords: bool = True


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    normalised = value.strip().lower()
    if normalised in {"1", "true", "t", "yes", "y"}:
        return True
    if normalised in {"0", "false", "f", "no", "n"}:
        return False
    return default


def load_configurations(csv_path: str | Path) -> list[MetadataExportConfig]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration CSV not found: {path}")

    configurations: list[MetadataExportConfig] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Configuration CSV must define column headers.")

        for row_number, row in enumerate(reader, start=2):
            metadata_id = (row.get("metadata_id") or "").strip()
            if not metadata_id:
                raise ValueError(
                    f"Row {row_number} missing mandatory 'metadata_id' value."
                )

            include_sources = _parse_bool(row.get("include_sources"), default=True)
            include_keywords = _parse_bool(row.get("include_keywords"), default=True)
            configurations.append(
                MetadataExportConfig(
                    metadata_id=metadata_id,
                    include_sources=include_sources,
                    include_keywords=include_keywords,
                )
            )
    if not configurations:
        raise ValueError("Configuration CSV did not contain any metadata records.")
    return configurations

