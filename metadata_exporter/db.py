"""
Project: LandIS Portal
Institution: Cranfield University
Author: Professor Stephen Hallett

Database access helpers for retrieving LandIS metadata assets.
"""

from __future__ import annotations

import os
from typing import Any
import importlib

Connection = Any
Cursor = Any


def init_oracle_client_if_available() -> None:
    """Initialise the Oracle client when a library directory is available.

    Returns:
        None. Side effects occur through driver initialisation.
    """
    lib_dir = os.environ.get("ORACLE_CLIENT_LIB_DIR")
    if lib_dir:
        driver = _get_driver()
        driver.init_oracle_client(lib_dir=lib_dir)


def _get_driver() -> Any:
    """Import the python-oracledb driver, raising a helpful error if missing.

    Returns:
        Loaded python-oracledb module reference.

    Raises:
        ModuleNotFoundError: If python-oracledb is not installed.
    """
    try:
        return importlib.import_module("oracledb")
    except ModuleNotFoundError:  # pragma: no cover - safety for missing dependency
        raise ModuleNotFoundError(
            "python-oracledb is required. Install it with `pip install oracledb`."
        )


def create_connection() -> "Connection":
    """Create a database connection using Oracle-related environment variables.

    Returns:
        Active Oracle database connection.

    Raises:
        EnvironmentError: If required credentials are absent.
    """
    driver = _get_driver()
    user = os.environ.get("ORACLE_USER")
    password = os.environ.get("ORACLE_PASSWORD")
    dsn = os.environ.get("ORACLE_DSN")

    if not user or not password or not dsn:
        raise EnvironmentError(
            "Environment variables ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN must be set."
        )

    init_oracle_client_if_available()
    return driver.connect(user=user, password=password, dsn=dsn)


def _rows_to_dicts(cursor: "Cursor") -> list[dict[str, Any]]:
    """Convert database cursor rows into dictionaries keyed by column name.

    Parameters:
        cursor: Database cursor containing row data and description metadata.

    Returns:
        Normalised rows keyed by lowercase column names.
    """
    column_names = [description[0].lower() for description in cursor.description]
    return [dict(zip(column_names, row, strict=True)) for row in cursor]


def fetch_main_record(
    connection: "Connection", metadata_id: str
) -> dict[str, Any] | None:
    """Fetch the main metadata record for a given identifier.

    Parameters:
        connection: Active Oracle database connection.
        metadata_id: Metadata identifier to locate.

    Returns:
        Mapping describing the primary metadata record, or None when missing.
    """
    sql = """
        SELECT
            METADATA_ID,
            GROUP_ID,
            TITLE,
            ABSTRACT,
            SUPPLEMENTAL_INFORMATION,
            CITATION_ID,
            PUBLICATION_DATE,
            STATUS_PROGRESS,
            UPDATE_FREQUENCY,
            SECURITY_CLASSIFICATION,
            WEST_BOUNDING_COORDINATE,
            EAST_BOUNDING_COORDINATE,
            NORTH_BOUNDING_COORDINATE,
            SOUTH_BOUNDING_COORDINATE,
            TEMPORAL_DATE_FROM,
            TEMPORAL_DATE_TO,
            METADATA_FACING
        FROM ADMIN.METADATA_MAIN
        WHERE METADATA_ID = :metadata_id
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, metadata_id=metadata_id)
        rows = _rows_to_dicts(cursor)
    return rows[0] if rows else None


def fetch_group(connection: "Connection", group_id: str) -> dict[str, Any] | None:
    """Retrieve the metadata group record associated with a group identifier.

    Parameters:
        connection: Active Oracle database connection.
        group_id: Identifier for the metadata group.

    Returns:
        Mapping of group attributes, or None if the group does not exist.
    """
    sql = """
        SELECT
            GROUP_ID,
            USE_CONSTRAINT,
            ACCESS_CONSTRAINT,
            PURPOSE,
            CONTACT_ID,
            METADATA_CONTACT_ID,
            ATTRIBUTE_ACCURACY_REPORT,
            THUMBNAIL
        FROM ADMIN.METADATA_GROUPS
        WHERE GROUP_ID = :group_id
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, group_id=group_id)
        rows = _rows_to_dicts(cursor)
    return rows[0] if rows else None


def fetch_contacts_for_ids(
    connection: "Connection", contact_ids: list[int | str]
) -> dict[int | str, dict[str, Any]]:
    """Fetch contact records for a collection of identifiers.

    Parameters:
        connection: Active Oracle database connection.
        contact_ids: Identifiers requiring contact lookups.

    Returns:
        Mapping from contact identifier to contact detail dictionaries.
    """
    if not contact_ids:
        return {}

    sql = """
        SELECT
            CONTACT_ID,
            CONTACT_ROLE,
            INDIVIDUAL_NAME,
            ORGANISATION_NAME,
            POSITION_NAME,
            VOICE_PHONE,
            FACSIMILE_PHONE,
            DELIVERY_POINT,
            CITY,
            ADMINISTRATIVE_AREA,
            POSTAL_CODE,
            COUNTRY,
            ELECTRONIC_MAIL_ADDRESS,
            HOURS_OF_SERVICE,
            CONTACT_INSTRUCTIONS
        FROM ADMIN.METADATA_CONTACTS
        WHERE CONTACT_ID IN ({placeholders})
    """
    placeholders = ", ".join([f":id{i}" for i in range(len(contact_ids))])
    formatted_sql = sql.format(placeholders=placeholders)
    bindings = {f"id{i}": contact_id for i, contact_id in enumerate(contact_ids)}

    with connection.cursor() as cursor:
        cursor.execute(formatted_sql, bindings)
        rows = _rows_to_dicts(cursor)

    return {row["contact_id"]: row for row in rows}


def fetch_citation(
    connection: "Connection", citation_id: str
) -> dict[str, Any] | None:
    """Retrieve a citation record for a supplied citation identifier.

    Parameters:
        connection: Active Oracle database connection.
        citation_id: Identifier for the citation to return.

    Returns:
        Mapping of citation fields, or None if no match is found.
    """
    sql = """
        SELECT
            CITATION_ID,
            CITATION_TITLE,
            CITATION_ORIGINATOR,
            CITATION_PUBDATE,
            CITATION_EDITION,
            CITATION_DATA_FORM,
            CITATION_SERIES,
            ISSUE_IDENTIFICATION,
            PUBLICATION_PLACE,
            PUBLISHER,
            ONLINE_LINKAGE
        FROM ADMIN.METADATA_CITATIONS
        WHERE CITATION_ID = :citation_id
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, citation_id=citation_id)
        rows = _rows_to_dicts(cursor)
    return rows[0] if rows else None


def fetch_attributes(
    connection: "Connection", metadata_id: str
) -> list[dict[str, Any]]:
    """Retrieve attribute metadata linked to a metadata identifier.

    Parameters:
        connection: Active Oracle database connection.
        metadata_id: Identifier for the parent metadata record.

    Returns:
        List of attribute dictionaries ordered for readability.
    """
    sql = """
        SELECT
            METADATA_ID,
            ATTRIBUTE_NAME,
            ATTRIBUTE_ALIAS,
            ATTRIBUTE_NO,
            ATTRIBUTE_DEFINITION,
            ATTRIBUTE_TYPE,
            ATTRIBUTE_WIDTH,
            ATTRIBUTE_PRECISION,
            ATTRIBUTE_SCALE,
            CODESET_NAME
        FROM ADMIN.METADATA_ATTRIBUTES
        WHERE METADATA_ID = :metadata_id
        ORDER BY ATTRIBUTE_NO NULLS LAST, ATTRIBUTE_NAME
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, metadata_id=metadata_id)
        return _rows_to_dicts(cursor)


def fetch_keywords(
    connection: "Connection", metadata_id: str
) -> list[dict[str, Any]]:
    """Retrieve keyword metadata linked to a metadata identifier.

    Parameters:
        connection: Active Oracle database connection.
        metadata_id: Identifier for the parent metadata record.

    Returns:
        List of keyword dictionaries grouped by type.
    """
    sql = """
        SELECT
            METADATA_ID,
            KEYWORD_TYPE,
            KEYWORD
        FROM ADMIN.METADATA_KEYWORDS
        WHERE METADATA_ID = :metadata_id
        ORDER BY KEYWORD_TYPE, KEYWORD
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, metadata_id=metadata_id)
        return _rows_to_dicts(cursor)


def fetch_sources(
    connection: "Connection", metadata_id: str
) -> list[dict[str, Any]]:
    """Retrieve source metadata linked to a metadata identifier.

    Parameters:
        connection: Active Oracle database connection.
        metadata_id: Identifier for the parent metadata record.

    Returns:
        List of source dictionaries joined to human-readable attributes.
    """
    sql = """
        SELECT
            ms.ID,
            ms.METADATA_ID,
            ms.SOURCE_ID,
            s.SOURCE_NAME,
            s.SOURCE_SCALE,
            s.SOURCE_MEDIA,
            s.SOURCE_CONTRIBUTION,
            s.CITATION_ID
        FROM ADMIN.METADATA_MAIN_SOURCE ms
        JOIN ADMIN.METADATA_SOURCES s
            ON s.SOURCE_ID = ms.SOURCE_ID
        WHERE ms.METADATA_ID = :metadata_id
        ORDER BY ms.ID
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, metadata_id=metadata_id)
        return _rows_to_dicts(cursor)


def fetch_source_citations(
    connection: "Connection", source_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    """Fetch citations related to multiple source identifiers.

    Parameters:
        connection: Active Oracle database connection.
        source_ids: Source identifiers requiring citation lookups.

    Returns:
        Mapping from source identifier to citation rows.
    """
    if not source_ids:
        return {}

    sql = """
        SELECT
            SOURCE_ID,
            CITATION_ID
        FROM ADMIN.METADATA_SOURCE_CITATION
        WHERE SOURCE_ID IN ({placeholders})
        ORDER BY SOURCE_ID
    """
    placeholders = ", ".join([f":id{i}" for i in range(len(source_ids))])
    formatted_sql = sql.format(placeholders=placeholders)
    bindings = {f"id{i}": source_id for i, source_id in enumerate(source_ids)}

    with connection.cursor() as cursor:
        cursor.execute(formatted_sql, bindings)
        rows = _rows_to_dicts(cursor)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["source_id"], []).append(row)
    return grouped


def fetch_citations_for_ids(
    connection: "Connection", citation_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Fetch citation records for a list of citation identifiers.

    Parameters:
        connection: Active Oracle database connection.
        citation_ids: Citation identifiers to fetch.

    Returns:
        Mapping from citation identifier to citation details.
    """
    if not citation_ids:
        return {}

    sql = """
        SELECT
            CITATION_ID,
            CITATION_TITLE,
            CITATION_ORIGINATOR,
            CITATION_PUBDATE,
            CITATION_EDITION,
            CITATION_DATA_FORM,
            CITATION_SERIES,
            ISSUE_IDENTIFICATION,
            PUBLICATION_PLACE,
            PUBLISHER,
            ONLINE_LINKAGE
        FROM ADMIN.METADATA_CITATIONS
        WHERE CITATION_ID IN ({placeholders})
    """
    placeholders = ", ".join([f":id{i}" for i in range(len(citation_ids))])
    formatted_sql = sql.format(placeholders=placeholders)
    bindings = {f"id{i}": citation_id for i, citation_id in enumerate(citation_ids)}

    with connection.cursor() as cursor:
        cursor.execute(formatted_sql, bindings)
        rows = _rows_to_dicts(cursor)

    return {row["citation_id"]: row for row in rows}


def fetch_metadata_bundle(
    connection: "Connection",
    metadata_id: str,
    include_sources: bool = True,
    include_keywords: bool = True,
) -> dict[str, Any]:
    """Compile the metadata bundle required for XML export routines.

    Parameters:
        connection: Active Oracle database connection.
        metadata_id: Identifier for the metadata record to export.
        include_sources: Flag controlling inclusion of source records.
        include_keywords: Flag controlling inclusion of keyword records.

    Returns:
        Aggregated metadata bundle ready for XML serialisation.
    """
    bundle: dict[str, Any] = {"metadata_id": metadata_id}

    main = fetch_main_record(connection, metadata_id)
    if main is None:
        raise LookupError(f"Metadata ID '{metadata_id}' not found in METADATA_MAIN.")
    bundle["main"] = main

    group = None
    if main.get("group_id"):
        group = fetch_group(connection, main["group_id"])
    bundle["group"] = group

    main_citation = None
    if main.get("citation_id"):
        main_citation = fetch_citation(connection, main["citation_id"])
    bundle["citation"] = main_citation

    bundle["group_contact"] = None
    bundle["metadata_contact"] = None

    contact_ids: list[int | str] = []
    if group:
        if group.get("contact_id") is not None:
            contact_ids.append(group["contact_id"])
        if group.get("metadata_contact_id") is not None:
            contact_ids.append(group["metadata_contact_id"])

    contact_lookup: dict[int | str, dict[str, Any]] = {}
    if contact_ids:
        unique_ids = list(dict.fromkeys(contact_ids))
        contact_lookup = fetch_contacts_for_ids(connection, unique_ids)

    if group:
        if group.get("contact_id") is not None:
            bundle["group_contact"] = contact_lookup.get(group["contact_id"])
        if group.get("metadata_contact_id") is not None:
            bundle["metadata_contact"] = contact_lookup.get(
                group["metadata_contact_id"]
            )

    bundle["attributes"] = fetch_attributes(connection, metadata_id)

    bundle["keywords"] = (
        fetch_keywords(connection, metadata_id) if include_keywords else []
    )

    sources = fetch_sources(connection, metadata_id) if include_sources else []
    bundle["sources"] = sources

    source_citation_map: dict[str, list[dict[str, Any]]] = {}
    citation_lookup: dict[str, dict[str, Any]] = {}
    if sources:
        source_ids = [source["source_id"] for source in sources]
        source_citation_map = fetch_source_citations(connection, source_ids)
        linked_citation_ids = {
            source["citation_id"]
            for source in sources
            if source.get("citation_id")
        }
        for rows in source_citation_map.values():
            for row in rows:
                linked_citation_ids.add(row["citation_id"])
        citation_lookup = fetch_citations_for_ids(
            connection, sorted(linked_citation_ids)
        )

    bundle["source_citations"] = source_citation_map
    bundle["citation_lookup"] = citation_lookup
    return bundle

