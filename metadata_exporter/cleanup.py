"""
Project: LandIS Portal
Institution: Cranfield University
Author: Professor Stephen Hallett

Utility for processing source database metadata tables:
- normalising quotation marks across Oracle metadata tables.
- updating metadata_ids to match the source database.

 usage: python -m metadata_exporter.cleanup --config config/cleanup_target.JSON
 options:
   --config CONFIG       Path to JSON configuration file describing cleanup targets.
   --env-file ENV_FILE   Optional path to a .env file containing Oracle credentials.
   --commit              Apply updates instead of running in dry-run mode.
   --verbose             Enable verbose logging for diagnostic purposes.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from textwrap import shorten
from typing import Iterable, Sequence

from . import db

LOGGER = logging.getLogger("metadata_cleanup")

# Map problematic punctuation to their ASCII equivalents.
_NORMALISATION_MAP: dict[str, str] = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2032": "'",
    "\u2035": "'",
    "\u0060": "'",
    "\u00b4": "'",
    "\u02bb": "'",
    "\u02bc": "'",
    "\u275b": "'",
    "\u275c": "'",
    "\u275f": "'",
    "\u2760": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2033": '"',
    "\u2036": '"',
    "\u00ab": '"',
    "\u00bb": '"',
    "\u02dd": '"',
    "\u275d": '"',
    "\u275e": '"',
    "\u301d": '"',
    "\u301e": '"',
    "\u301f": '"',
    "\u00bf": "'",
}

_TRANSLATION_TABLE = str.maketrans(_NORMALISATION_MAP)


@dataclass(slots=True)
class CleanupTarget:
    """Describe a table/column pair subject to normalisation.

    Attributes:
        table: Fully qualified table name, for example `ADMIN.METADATA_MAIN`.
        column: Column name that requires normalisation.
        where: Optional SQL WHERE clause predicate to narrow the scan.
        identifier: Optional column name to include in log output for traceability.
    """

    table: str
    column: str
    where: str | None = None
    identifier: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, str]) -> "CleanupTarget":
        """Construct a CleanupTarget from a JSON configuration payload.

        Parameters:
            payload: Dictionary containing table, column, and optional fields.

        Returns:
            Configured CleanupTarget instance.

        Raises:
            ValueError: When required keys are missing from the payload.
        """
        try:
            table = payload["table"]
            column = payload["column"]
        except KeyError as error:
            message = (
                "Target entries must define at least 'table' and 'column'. "
                f"Missing key: {error.args[0]}"
            )
            raise ValueError(message) from error
        where = payload.get("where")
        identifier = payload.get("identifier")
        return cls(table=table, column=column, where=where, identifier=identifier)


def _load_targets(config_path: Path) -> list[CleanupTarget]:
    """Load cleanup targets from a JSON configuration file.

    Parameters:
        config_path: Path to the JSON configuration file.

    Returns:
        List of CleanupTarget instances parsed from the configuration.

    Raises:
        ValueError: When the configuration does not contain a valid array of targets.
    """
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        raise ValueError("Configuration file must contain a JSON array of targets.")
    targets = [CleanupTarget.from_payload(item) for item in payload]  # type: ignore[arg-type]
    if not targets:
        raise ValueError("Configuration file defines no cleanup targets.")
    return targets


def normalise_quotes(value: str) -> str:
    """Normalise quotation marks and related glyphs to ASCII equivalents.

    Converts curly quotes, smart apostrophes, and other problematic Unicode
    quotation marks to their nearest ASCII equivalents (' and ").

    Parameters:
        value: Input string potentially containing smart quotes.

    Returns:
        String with all problematic quotation marks replaced by ASCII equivalents.
    """
    return value.translate(_TRANSLATION_TABLE)


def _configure_logger(verbose: bool) -> None:
    """Configure the module logger for console output.

    Parameters:
        verbose: When True, enable debug-level logging; otherwise use INFO level.

    Returns:
        None. The global logger is configured in place.
    """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)


def _summarise(text: str, width: int = 120) -> str:
    """Truncate text to a specified width for log output.

    Parameters:
        text: Input string to truncate.
        width: Maximum width before truncation.

    Returns:
        Truncated string with an ellipsis placeholder if shortened.
    """
    return shorten(text, width=width, placeholder="…")


def _select_rows(
    cursor: "db.Cursor", target: CleanupTarget
) -> Iterable[tuple[str, str | None, str | None]]:
    """Select rows from a target table for processing.

    Parameters:
        cursor: Database cursor for executing queries.
        target: CleanupTarget describing the table and column to scan.

    Yields:
        Tuples of (rowid, column_value, identifier) for each matching row.
    """
    select_columns = ["ROWID", target.column]
    if target.identifier:
        select_columns.append(target.identifier)
    select_clause = ", ".join(select_columns)
    sql = f"SELECT {select_clause} FROM {target.table}"
    if target.where:
        sql += f" WHERE {target.where}"
    cursor.execute(sql)
    for row in cursor:
        rowid = row[0]
        value = row[1]
        identifier = row[2] if target.identifier else None
        yield rowid, value, identifier


def _apply_updates(
    connection: "db.Connection",
    target: CleanupTarget,
    dry_run: bool,
) -> int:
    """Process a cleanup target and apply normalisation updates.

    Scans the specified table column, identifies rows requiring normalisation,
    logs all proposed changes, and optionally applies updates to the database.

    Parameters:
        connection: Active database connection.
        target: CleanupTarget describing the table and column to process.
        dry_run: When True, log changes without applying updates.

    Returns:
        Number of rows updated (zero in dry-run mode).
    """
    total_updates = 0
    with connection.cursor() as cursor:
        rows = list(_select_rows(cursor, target))

    updates: list[tuple[str, str, str | None, str]] = []
    for rowid, current_value, identifier in rows:
        if current_value is None:
            continue
        converted = normalise_quotes(str(current_value))
        if converted != str(current_value):
            updates.append((rowid, converted, identifier, str(current_value)))

    if not updates:
        LOGGER.info("No changes required for %s.%s", target.table, target.column)
        return 0

    for rowid, converted, identifier, original in updates:
        label = identifier if identifier is not None else f"ROWID={rowid}"
        LOGGER.info(
            "%s.%s (%s): %s -> %s",
            target.table,
            target.column,
            label,
            _summarise(original),
            _summarise(converted),
        )

    if dry_run:
        LOGGER.info(
            "Dry-run active: %s pending update(s) recorded for %s.%s",
            len(updates),
            target.table,
            target.column,
        )
        return 0

    with connection.cursor() as cursor:
        sql = f"UPDATE {target.table} SET {target.column} = :value WHERE ROWID = :rowid"
        for rowid, converted, _, _ in updates:
            cursor.execute(sql, value=converted, rowid=rowid)
            total_updates += 1
    LOGGER.info(
        "Applied %s update(s) for %s.%s", total_updates, target.table, target.column
    )
    return total_updates


def parse_arguments(args: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the cleanup utility.

    Parameters:
        args: Optional sequence of argument strings for testing purposes.

    Returns:
        Parsed argument namespace ready for downstream consumption.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Normalise smart quotes within configured Oracle metadata columns. "
            "Defaults to a dry-run; supply --commit to apply changes."
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to JSON configuration file describing cleanup targets.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Optional path to a .env file containing Oracle credentials.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Apply updates instead of running in dry-run mode.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for diagnostic purposes.",
    )
    return parser.parse_args(args)


def load_environment(env_file: Path | None) -> None:
    """Load environment variables from an optional .env file.

    Parameters:
        env_file: Path to a dotenv file; ignored when None or missing.

    Returns:
        None. Environment variables are loaded for the current process.

    Raises:
        ModuleNotFoundError: When python-dotenv is unavailable and a file is provided.
    """
    if env_file is None:
        return
    if not env_file.exists():
        LOGGER.debug("No .env file found at %s; using existing environment.", env_file)
        return
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ModuleNotFoundError as error:  # pragma: no cover - optional dependency
        raise ModuleNotFoundError(
            "python-dotenv is required to load environment files. "
            "Install it with `pip install python-dotenv`."
        ) from error
    load_dotenv(env_file)
    LOGGER.debug("Environment variables loaded from %s", env_file)


def run_cleanup(args: argparse.Namespace) -> int:
    """Execute the cleanup process for all configured targets.

    Loads configuration, connects to the database, processes each target,
    and either commits or rolls back changes based on dry-run mode.

    Parameters:
        args: Parsed command-line arguments.

    Returns:
        Total number of rows updated across all targets.

    Raises:
        FileNotFoundError: When the configuration file is missing.
    """
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    targets = _load_targets(config_path)
    load_environment(Path(args.env_file) if args.env_file else None)

    dry_run = not args.commit
    total_updates = 0

    with db.create_connection() as connection:
        connection.autocommit = False  # type: ignore[attr-defined]
        for target in targets:
            total_updates += _apply_updates(connection, target, dry_run=dry_run)
        if dry_run:
            connection.rollback()
            LOGGER.info("Rollback complete (dry-run).")
        else:
            connection.commit()
            LOGGER.info("Committed %s update(s) in total.", total_updates)
    return total_updates


def main() -> None:
    """Entry point for command-line execution of the cleanup utility."""
    args = parse_arguments()
    _configure_logger(verbose=args.verbose)
    try:
        updates = run_cleanup(args)
    except Exception as error:  # pragma: no cover - safety net
        LOGGER.error("Cleanup failed: %s", error, exc_info=args.verbose)
        raise
    if not args.commit:
        LOGGER.info(
            "Dry-run completed. Re-run with --commit after reviewing the proposed changes."
        )
    else:
        LOGGER.info("Cleanup finished. %s row(s) updated.", updates)


if __name__ == "__main__":
    main()

