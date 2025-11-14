# LandIS Portal - Metadata Exporter

Utility scripts for exporting LandIS metadata records to ISO 19139 XML files.

Project: LandIS Portal
Institution: Cranfield University
Author: Professor Stephen Hallett
http://www.landis.org.uk


## Prerequisites

- Python 3.11 or newer
- Oracle credentials with access to the required metadata tables
- Optional: Oracle Instant Client libraries if they are not already available on the host

## Initial Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   ```
2. Activate the environment:
   - **Command Prompt:** `venv\Scripts\activate.bat`
   - **PowerShell:** `.\venv\Scripts\Activate.ps1`
   - **Git Bash or other POSIX shells:** `source venv/Scripts/activate`
3. Install the two key dependencies:
   ```
   pip install oracledb python-dotenv
   ```

## Environment Variables

The exporter reads Oracle connection settings from the environment. These are kept  in a `.env` file alongside the project.

```
ORACLE_USER=<USER>
ORACLE_PASSWORD=<PASSWORD>
ORACLE_DSN=<DSN>
```

The CLI automatically loads the `.env` file supplied via `--env-file` (defaults to `.env`).

## Running the Exporter

From the project root with the virtual environment active:

```
python -m metadata_exporter.export_metadata --config config\metadata_ids.csv --output-dir output
```

- Use `--dry-run` to fetch data without writing XML files.
- Override `--config`, `--output-dir`, or `--env-file` to point at alternative locations.

Each metadata identifier listed in `config\metadata_ids.csv` results in one XML file under the output directory. Comment lines beginning with `#` are ignored.

## Quote Cleanup Utility

Mis-encoded punctuation occasionally finds its way into title and abstract fields. The quote cleanup utility normalises curly quotation marks and related glyphs to plain ASCII quotes while logging every proposed change.

### Configuration

List the tables and columns you wish to scan in `config/cleanup_target.JSON`. Each entry supports:

- `table`: Fully qualified table name, for example `ADMIN.METADATA_MAIN`.
- `column`: Column that requires normalisation.
- `identifier` (optional): Additional column to include in the log output for easier traceability.
- `where` (optional): SQL predicate narrowing the scan, for example `METADATA_ID LIKE 'NATMAP%'`.

### Dry-run and commit workflow

1. Review or amend the sample configuration in `config/cleanup_target.JSON`.
2. Execute a dry-run to review proposed changes:
   ```
   python -m metadata_exporter.cleanup --config config/cleanup_target.JSON
   ```
3. After reviewing the log output, re-run with `--commit` to apply the updates atomically:
   ```
   python -m metadata_exporter.cleanup --config config/cleanup_target.JSON --commit
   ```

The script uses the same environment variables as the exporter; supply an alternate `.env` file via `--env-file` when required.

## Oracle Instant Client (Optional)

If the host requires Instant Client, download and extract it, then point `ORACLE_CLIENT_LIB_DIR` at the extracted folder. The exporter initialises the client automatically when the variable is present.

## Troubleshooting

- **Missing `python-oracledb`:** Install with `pip install oracledb`.
- **`.env` not loading:** Ensure `python-dotenv` is installed (`pip install python-dotenv`) or export variables via the shell.
- **Permission errors in PowerShell:** Run `Set-ExecutionPolicy -Scope Process RemoteSigned` before activation.

## Development Notes

- Code follows `black`-compatible formatting and PEP 8 guidelines.
- Keep new features modular to aid future expandability (for example, Vision requests).
- Run the unit tests with `python -m pytest`.

## Project Structure

```
metadata/
├── config/
│   ├── cleanup_target.JSON    # Configuration for quote normalisation
│   └── metadata_ids.csv       # List of metadata IDs to export
├── helper_files/
│   ├── HORIZONS.xml           # Example XML output
│   └── metadata_schema.sql    # Database schema reference
├── metadata_exporter/
│   ├── __init__.py
│   ├── cleanup.py             # Quote normalisation utility
│   ├── config_loader.py       # CSV configuration loading
│   ├── db.py                  # Database connection and queries
│   ├── export_metadata.py     # Main export CLI
│   └── xml_builder.py         # ISO 19139 XML construction
├── output/                    # Generated XML files
├── tests/
│   └── test_quote_cleanup.py  # Unit tests for normalisation
└── README.md
```
