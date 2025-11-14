"""
Project: LandIS Portal
Institution: Cranfield University
Author: Professor Stephen Hallett

Command-line interface for exporting LandIS metadata to ISO 19139 XML.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import config_loader, db, xml_builder

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]

LOGGER = logging.getLogger("metadata_exporter")


def parse_arguments() -> argparse.Namespace:
    """Define and parse command-line options for the exporter.

    Returns:
        Parsed argument namespace ready for downstream consumption.
    """
    parser = argparse.ArgumentParser(
        description="Export LandIS metadata records to ISO 19139 XML files."
    )
    parser.add_argument(
        "--config",
        default="config/metadata_ids.csv",
        help="Path to CSV file listing metadata_ids to export.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where XML files will be written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch records without writing XML files, useful for validation.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file containing ORACLE_* variables (ignored if missing).",
    )
    return parser.parse_args()


def ensure_output_directory(path: Path) -> None:
    """Ensure the output directory exists before writing files.

    Parameters:
        path: Directory path intended to hold generated XML files.

    Returns:
        None. The directory is created if required.
    """
    path.mkdir(parents=True, exist_ok=True)


def build_logger(verbose: bool = False) -> None:
    """Configure the module logger for console output.

    Parameters:
        verbose: When True, enable debug-level logging output.

    Returns:
        None. Global logger is configured in-place.
    """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)


def load_environment(env_file: Path | None) -> None:
    """Load environment variables from an optional .env file.

    Parameters:
        env_file: Path to a dotenv file; ignored when None or missing.

    Returns:
        None. Environment variables are loaded for the current process.

    Raises:
        ModuleNotFoundError: When python-dotenv is unavailable.
    """
    if env_file is None:
        return
    if not env_file.exists():
        LOGGER.debug("No .env file found at %s; using existing environment.", env_file)
        return
    if load_dotenv is None:
        raise ModuleNotFoundError(
            "python-dotenv is required to load environment files. Install it with `pip install python-dotenv`."
        )
    load_dotenv(env_file)
    LOGGER.debug("Environment variables loaded from %s", env_file)


def export_metadata_records(
    configuration_path: Path, output_directory: Path, dry_run: bool = False
) -> list[Path]:
    """Export metadata records to XML based on configuration entries.

    Parameters:
        configuration_path: CSV file describing metadata identifiers to export.
        output_directory: Destination directory for generated XML files.
        dry_run: When True, skip file writing while exercising data retrieval.

    Returns:
        List of paths for the XML files written during the session.
    """
    configs = config_loader.load_configurations(configuration_path)
    LOGGER.info("Loaded %s metadata configurations from %s", len(configs), configuration_path)

    ensure_output_directory(output_directory)

    written_files: list[Path] = []
    with db.create_connection() as connection:
        for config in configs:
            LOGGER.info("Exporting metadata ID %s", config.metadata_id)
            bundle = db.fetch_metadata_bundle(
                connection,
                metadata_id=config.metadata_id,
                include_sources=config.include_sources,
                include_keywords=config.include_keywords,
            )

            tree = xml_builder.build_metadata_tree(bundle)
            xml_builder.format_tree_for_output(tree)
            if dry_run:
                LOGGER.debug("Dry-run enabled; skipping write for %s", config.metadata_id)
                continue

            output_path = output_directory / f"{config.metadata_id}.xml"
            tree.write(output_path, encoding="utf-8", xml_declaration=True)
            LOGGER.info("Wrote %s", output_path)
            written_files.append(output_path)
    return written_files


def main() -> None:
    """Entry point for command-line execution of the exporter."""
    args = parse_arguments()
    build_logger()
    load_environment(Path(args.env_file) if args.env_file else None)
    exported = export_metadata_records(
        configuration_path=Path(args.config),
        output_directory=Path(args.output_dir),
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        LOGGER.info("Export completed: %s files written.", len(exported))


if __name__ == "__main__":
    main()

