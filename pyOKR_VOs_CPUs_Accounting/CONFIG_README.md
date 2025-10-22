# Configuration (minimal)

Place your Google service account JSON locally (do NOT commit it):

- Default location: `pyOKR_VOs_CPUs_Accounting/.config/service_account.json`
- Template: `pyOKR_VOs_CPUs_Accounting/.config/service_account.json.template`

Required environment variables (most common):

- `SERVICE_ACCOUNT_FILE` — path to service account JSON (default above)
- `GOOGLE_SHEET_NAME` — target spreadsheet name
- `GOOGLE_CLOUD_WORKSHEET`, `GOOGLE_HTC_WORKSHEET` — worksheet names
- `ACCOUNTING_SERVER_URL`, `ACCOUNTING_SCOPE`, `ACCOUNTING_METRIC` — accounting API settings
- `DATE_FROM`, `DATE_TO` — reporting period

Quick test/run

Use the repository venv or Poetry; example:

```bash
./pyOKR_VOs_CPUs_Accounting/.venv/bin/python -m pytest -q
```

If you need a helper to copy the template into `.config/` without committing
credentials, tell me and I'll add a small script.
# Local config and service account

This file documents how to create a `service_account.json` locally from the template without committing secrets.

The `.config/` directory is excluded from version control. Copy the template or download the service account file from Google Cloud and place it in `.config/service_account.json`.

Steps:

1. Copy the template (if present) to the local config folder:

   cp .config/service_account.json.template .config/service_account.json

2. Alternatively, download the JSON key from the Google Cloud Console and save it as:

   .config/service_account.json

3. Set environment variables if needed:

   export SERVICE_ACCOUNT_PATH="${PWD}/.config/"
   export SERVICE_ACCOUNT_FILE="${SERVICE_ACCOUNT_PATH}service_account.json"

4. Run the application or tests that need the service account.

Security note: do NOT commit `.config/service_account.json` to Git. This repository's `.gitignore` already excludes the `.config/` directory.

## Environment variables

The project uses a few environment variables. These are typically set in files under `.config/` (for local development) or exported in your shell.

Below are the variables found in the existing `.config` files and a short description for each:

- SERVICE_ACCOUNT_FILE: Path to the local `service_account.json` file (e.g. `.config/service_account.json`).
- LOG: Logging level used by the application (e.g. `INFO`, `DEBUG`).
- DATE_FROM / DATE_TO: Reporting date range used by some accounting scripts.
- SSL_CHECK: Toggle SSL checks (True/False) for HTTP requests.

- ACCOUNTING_SERVER_URL: URL of the accounting server to fetch data from.
- ACCOUNTING_SCOPE: Scope of accounting (`cloud` / `htc` etc.).
- ACCOUNTING_METRIC: Metric to request from the accounting server.
- ACCOUNTING_LOCAL_JOB_SELECTOR: Local job filter setting.
- ACCOUNTING_VO_GROUP_SELECTOR: VO group selector used by the accounting API.
- ACCOUNTING_DATA_SELECTOR: Data format expected from the accounting API (e.g. `JSON`).

- GOOGLE_SHEET_NAME: Name of the Google Sheet used for reports.
- GOOGLE_CLOUD_WORKSHEET / GOOGLE_HTC_WORKSHEET: Worksheet names inside the Google Sheet.

If you add or change any of these variables locally, update your `.config/.env*` files accordingly.
