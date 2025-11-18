from __future__ import annotations

"""
Project: LandIS Portal
Institution: Cranfield University
Author: Professor Stephen Hallett

Configuration loading utilities for metadata export workflows.
"""

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass(frozen=True, slots=True)
class MetadataExportConfig:
    """Configuration for exporting a single metadata record.

    Attributes:
        metadata_id: Unique identifier for the metadata record to export.
        include_sources: Whether to include source lineage information in the export.
        include_keywords: Whether to include keyword metadata in the export.
    """

    metadata_id: str
    include_sources: bool = True
    include_keywords: bool = True


def _parse_bool(value: str | None, default: bool) -> bool:
    """Convert a string value to a boolean, falling back to a default.

    Parameters:
        value: Raw value sourced from the configuration CSV.
        default: Fallback applied when the value is blank or unrecognised.

    Returns:
        Normalised boolean reflecting the input or default.
    """
    if value is None or value == "":
        return default
    normalised = value.strip().lower()
    if normalised in {"1", "true", "t", "yes", "y"}:
        return True
    if normalised in {"0", "false", "f", "no", "n"}:
        return False
    return default


def load_configurations(csv_path: str | Path) -> list[MetadataExportConfig]:
    """Load export configurations from a CSV file path.

    Parameters:
        csv_path: Filesystem path to the configuration CSV.

    Returns:
        Collection of export configuration records.

    Notes:
        Lines beginning with '#' are treated as comments and ignored.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration CSV not found: {path}")

    configurations: list[MetadataExportConfig] = []
    with path.open(newline="", encoding="utf-8") as handle:
        non_comment_lines = (
            line for line in handle if not line.lstrip().startswith("#")
        )
        reader = csv.DictReader(non_comment_lines)
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

