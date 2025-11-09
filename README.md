# LandIS Portal - Metadata Exporter

Utility scripts for exporting LandIS metadata records to ISO 19139 XML files.

http://www.landis.org.uk

Author: Stephen Hallett, Cranfield University

Date: 9-11-2025

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
3. Install dependencies:
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

Each metadata identifier listed in `config\metadata_ids.csv` results in one XML file under the output directory.

## Oracle Instant Client (Optional)

If the host requires Instant Client, download and extract it, then point `ORACLE_CLIENT_LIB_DIR` at the extracted folder. The exporter initialises the client automatically when the variable is present.

## Troubleshooting

- **Missing `python-oracledb`:** Install with `pip install oracledb`.
- **`.env` not loading:** Ensure `python-dotenv` is installed (`pip install python-dotenv`) or export variables via the shell.
- **Permission errors in PowerShell:** Run `Set-ExecutionPolicy -Scope Process RemoteSigned` before activation.

## Development Notes

- Code follows `black`-compatible formatting and PEP 8 guidelines.
- Keep new features modular to aid future expandability (for example, Vision requests).


