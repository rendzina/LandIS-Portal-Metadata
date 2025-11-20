# LandIS Portal - Metadata Exporter System Architecture

This document provides detailed system architecture diagrams for the LandIS Portal Metadata Exporter.

## System Overview

The metadata exporter system consists of two main workflows:

1. **Metadata Export Workflow**: Exports metadata records from Oracle database to ISO 19139-compliant XML files
2. **Quote Cleanup Workflow**: Normalises smart quotes and special characters in database metadata fields

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Input["Input Configuration"]
        CSV["CSV Config<br/>(metadata_ids.csv)"]
        ENV[".env File<br/>(Oracle Credentials)"]
        JSON["JSON Config<br/>(cleanup_target.JSON)"]
    end

    subgraph CLI["Command-Line Interface"]
        EXPORT["export_metadata.py<br/>(Main Export CLI)"]
        CLEANUP["cleanup.py<br/>(Quote Cleanup Utility)"]
    end

    subgraph Core["Core Modules"]
        CONFIG_LOADER["config_loader.py<br/>(CSV Parser)"]
        DB["db.py<br/>(Database Access)"]
        XML_BUILDER["xml_builder.py<br/>(ISO 19139 Builder)"]
    end

    subgraph Oracle["Oracle Database"]
        MAIN["METADATA_MAIN"]
        GROUPS["METADATA_GROUPS"]
        CONTACTS["METADATA_CONTACTS"]
        CITATIONS["METADATA_CITATIONS"]
        ATTRIBUTES["METADATA_ATTRIBUTES"]
        KEYWORDS["METADATA_KEYWORDS"]
        SOURCES["METADATA_SOURCES"]
    end

    subgraph Output["Output"]
        XML_FILES["ISO 19139 XML Files<br/>(output/)"]
    end

    CSV --> CONFIG_LOADER
    ENV --> DB
    JSON --> CLEANUP
    
    CONFIG_LOADER --> EXPORT
    EXPORT --> DB
    EXPORT --> XML_BUILDER
    CLEANUP --> DB
    
    DB --> MAIN
    DB --> GROUPS
    DB --> CONTACTS
    DB --> CITATIONS
    DB --> ATTRIBUTES
    DB --> KEYWORDS
    DB --> SOURCES
    
    XML_BUILDER --> XML_FILES
    
    style CSV fill:#e1f5ff
    style ENV fill:#e1f5ff
    style JSON fill:#e1f5ff
    style EXPORT fill:#fff4e1
    style CLEANUP fill:#fff4e1
    style XML_FILES fill:#e8f5e9
    style Oracle fill:#fce4ec
```

## Metadata Export Workflow

The export process reads configuration, connects to the database, fetches metadata records, and generates ISO 19139 XML files.

```mermaid
flowchart LR
    START([Start Export]) --> LOAD_CONFIG[Load CSV Configuration]
    LOAD_CONFIG --> LOAD_ENV[Load Environment Variables]
    LOAD_ENV --> CONNECT[Connect to Oracle DB]
    CONNECT --> LOOP{For Each<br/>Metadata ID}
    LOOP --> FETCH[Fetch Metadata Bundle]
    FETCH --> BUILD[Build ISO 19139 XML Tree]
    BUILD --> FORMAT[Format & Indent XML]
    FORMAT --> DRY{Dry Run?}
    DRY -->|Yes| LOG[Log Output]
    DRY -->|No| WRITE[Write XML File]
    LOG --> NEXT{More IDs?}
    WRITE --> NEXT
    NEXT -->|Yes| LOOP
    NEXT -->|No| END([Export Complete])
    
    style START fill:#c8e6c9
    style END fill:#c8e6c9
    style DRY fill:#fff9c4
```

## Quote Cleanup Workflow

The cleanup process scans database tables for smart quotes and normalises them to ASCII equivalents.

```mermaid
flowchart LR
    START([Start Cleanup]) --> LOAD_JSON[Load JSON Configuration]
    LOAD_JSON --> LOAD_ENV[Load Environment Variables]
    LOAD_ENV --> CONNECT[Connect to Oracle DB]
    CONNECT --> LOOP{For Each<br/>Target Table/Column}
    LOOP --> SCAN[Scan Rows for<br/>Smart Quotes]
    SCAN --> NORMALISE[Normalise Quotes]
    NORMALISE --> LOG[Log Proposed Changes]
    LOG --> COMMIT{Commit Mode?}
    COMMIT -->|No| ROLLBACK[Rollback Transaction]
    COMMIT -->|Yes| UPDATE[Update Database]
    ROLLBACK --> NEXT{More Targets?}
    UPDATE --> NEXT
    NEXT -->|Yes| LOOP
    NEXT -->|No| END([Cleanup Complete])
    
    style START fill:#c8e6c9
    style END fill:#c8e6c9
    style COMMIT fill:#fff9c4
```

## Metadata Bundle Assembly

When exporting a metadata record, the system assembles a comprehensive bundle from multiple related database tables:

```mermaid
flowchart TD
    METADATA_ID[Metadata ID] --> FETCH_MAIN[Fetch Main Record]
    FETCH_MAIN --> CHECK_GROUP{Group ID<br/>Present?}
    CHECK_GROUP -->|Yes| FETCH_GROUP[Fetch Group Record]
    CHECK_GROUP -->|No| SKIP_GROUP[Skip Group]
    FETCH_GROUP --> FETCH_CONTACTS[Fetch Contact Records]
    SKIP_GROUP --> FETCH_CITATION
    FETCH_MAIN --> CHECK_CITATION{Citation ID<br/>Present?}
    CHECK_CITATION -->|Yes| FETCH_CITATION[Fetch Citation]
    CHECK_CITATION -->|No| SKIP_CITATION[Skip Citation]
    FETCH_CITATION --> FETCH_ATTRIBUTES[Fetch Attributes]
    FETCH_CONTACTS --> FETCH_ATTRIBUTES
    SKIP_CITATION --> FETCH_ATTRIBUTES
    FETCH_ATTRIBUTES --> CHECK_KEYWORDS{Include<br/>Keywords?}
    CHECK_KEYWORDS -->|Yes| FETCH_KEYWORDS[Fetch Keywords]
    CHECK_KEYWORDS -->|No| SKIP_KEYWORDS[Skip Keywords]
    FETCH_KEYWORDS --> CHECK_SOURCES{Include<br/>Sources?}
    SKIP_KEYWORDS --> CHECK_SOURCES
    CHECK_SOURCES -->|Yes| FETCH_SOURCES[Fetch Sources]
    CHECK_SOURCES -->|No| SKIP_SOURCES[Skip Sources]
    FETCH_SOURCES --> FETCH_SOURCE_CITATIONS[Fetch Source Citations]
    FETCH_SOURCE_CITATIONS --> BUNDLE[Complete Metadata Bundle]
    SKIP_SOURCES --> BUNDLE
    
    style BUNDLE fill:#c8e6c9
    style METADATA_ID fill:#e1f5ff
```

## Component Responsibilities

### Command-Line Interfaces

- **export_metadata.py**: Main entry point for metadata export operations
  - Parses command-line arguments
  - Loads configuration and environment variables
  - Orchestrates the export process
  - Handles logging and error reporting

- **cleanup.py**: Quote normalisation utility
  - Loads cleanup target configuration
  - Scans database tables for smart quotes
  - Applies normalisation with optional dry-run mode
  - Manages database transactions

### Core Modules

- **config_loader.py**: Configuration management
  - Parses CSV export configuration files
  - Validates configuration entries
  - Provides structured configuration objects

- **db.py**: Database access layer
  - Manages Oracle database connections
  - Provides query functions for all metadata tables
  - Assembles complete metadata bundles
  - Handles connection lifecycle

- **xml_builder.py**: XML generation
  - Constructs ISO 19139-compliant XML structures
  - Maps database records to XML elements
  - Handles namespaces and formatting
  - Generates complete metadata documents

## Database Schema Relationships

The system queries the following Oracle database tables:

- **METADATA_MAIN**: Primary metadata records
- **METADATA_GROUPS**: Group-level metadata and constraints
- **METADATA_CONTACTS**: Contact information for groups and metadata
- **METADATA_CITATIONS**: Citation information for datasets
- **METADATA_ATTRIBUTES**: Attribute definitions and schema information
- **METADATA_KEYWORDS**: Keyword classifications
- **METADATA_SOURCES**: Source lineage information
- **METADATA_MAIN_SOURCE**: Junction table linking metadata to sources
- **METADATA_SOURCE_CITATION**: Junction table linking sources to citations

## Data Flow Summary

1. **Configuration Input**: CSV or JSON configuration files define what to process
2. **Environment Setup**: `.env` file provides Oracle database credentials
3. **Database Connection**: System connects to Oracle using python-oracledb
4. **Data Retrieval**: Queries fetch related records from multiple tables
5. **Data Assembly**: Records are assembled into structured bundles
6. **XML Generation**: Bundles are transformed into ISO 19139 XML format
7. **Output**: XML files are written to the specified output directory

## Error Handling

- Database connection errors are caught and reported with helpful messages
- Missing configuration files raise `FileNotFoundError` with clear paths
- Invalid configuration data raises `ValueError` with specific details
- Missing metadata records raise `LookupError` with the metadata ID
- All errors are logged with appropriate context for debugging

