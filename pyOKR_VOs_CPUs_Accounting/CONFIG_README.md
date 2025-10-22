Local configuration (service account)

This short file explains where to place your Google service account JSON and
Google service account file when running the tooling in this repository.

Where to keep the service account

- Default path (recommended): `pyOKR_VOs_CPUs_Accounting/.config/service_account.json`.
- A template is provided: `pyOKR_VOs_CPUs_Accounting/.config/service_account.json.template`.
- DO NOT commit `*.json` credentials to version control. The `.config/` folder is
  excluded by `.gitignore`.

Create the local service account file

1. Copy the template (if present):

   cp pyOKR_VOs_CPUs_Accounting/.config/service_account.json.template pyOKR_VOs_CPUs_Accounting/.config/service_account.json

2. Populate it with the values from your Google Cloud service account JSON.

Common environment variables

- SERVICE_ACCOUNT_FILE: Path to the JSON file (default `.config/service_account.json`).
- SERVICE_ACCOUNT_PATH: Optional directory containing the account file.
- GOOGLE_SHEET_NAME: Spreadsheet name used by the Google Sheets integration.
- GOOGLE_CLOUD_WORKSHEET / GOOGLE_HTC_WORKSHEET: Worksheet names inside the sheet.
- ACCOUNTING_SERVER_URL, ACCOUNTING_SCOPE, ACCOUNTING_METRIC: Accounting API settings.
- DATE_FROM, DATE_TO: Reporting period.

Run tests

- Use the project's venv or Poetry:

  ./pyOKR_VOs_CPUs_Accounting/.venv/bin/python -m pytest -q

If you'd like, I can add a helper script to create `.config/` from the template
without copying credentials into the repo.

- Place your service account JSON at: `.config/service_account.json` relative to the
  repository root (this path is the default used by tests and tooling).

Security note

- The repository intentionally does NOT track `pyOKR_VOs_CPUs_Accounting/.config/service_account.json`.
- The file contains a private key and other credentials. Keep it out of version control.

How to create the file from the template

1. Copy the template shipped with the repository:
   - `cp pyOKR_VOs_CPUs_Accounting/.config/service_account.json.template pyOKR_VOs_CPUs_Accounting/.config/service_account.json`
2. Populate the fields in the copied file with values from the Google service
   account you create in your Cloud Console.
3. Keep the file local and never commit it. The repository's `.gitignore` already
   excludes `.config/service_account.json`.

Environment variables required (summary)

- SERVICE_ACCOUNT_FILE: Path to the JSON file (default `.config/service_account.json`)
- SERVICE_ACCOUNT_PATH: Directory path where the JSON can be found (optional)
- GOOGLE_SHEET_NAME: Spreadsheet name used by the Google Sheets integration
- GOOGLE_CLOUD_WORKSHEET / GOOGLE_HTC_WORKSHEET: Worksheet names
- ACCOUNTING_SERVER_URL, ACCOUNTING_SCOPE, ACCOUNTING_METRIC, DATE_FROM, DATE_TO:
  Required for the accounting data fetching

Running tests locally

- Set up a Python virtual environment and install requirements (see `pyOKR_VOs_CPUs_Accounting/README.md`).
- Ensure the service account file exists at the path configured in `SERVICE_ACCOUNT_FILE` or use the template.
- Run tests with: `poetry run pytest -q` or the project's venv python: `./pyOKR_VOs_CPUs_Accounting/.venv/bin/python -m pytest -q`.

If you would like me to add extra helper scripts to create the `.config` folder and
populate a safe sample (without secrets), say so and I will add them.

# Local configuration (service account)

This file explains where to keep your Google service account JSON locally and
how to configure the basic environment variables used by the package.

Quick summary

- Keep the service account JSON out of version control. Default path used by the
  code and tests: `pyOKR_VOs_CPUs_Accounting/.config/service_account.json`.
- A template is provided at `pyOKR_VOs_CPUs_Accounting/.config/service_account.json.template`.
- The repository root `CHANGELOG.md` contains project-level notes; use it for
  release/change information.

Create the local service account file

1. Copy the template:

   cp pyOKR_VOs_CPUs_Accounting/.config/service_account.json.template pyOKR_VOs_CPUs_Accounting/.config/service_account.json

2. Populate the file with credentials from your Google Cloud service account.
3. Ensure `.config/service_account.json` remains local and is NOT committed.

Environment variables (commonly used)

- SERVICE_ACCOUNT_FILE: Path to the service account JSON (default `.config/service_account.json`).
- SERVICE_ACCOUNT_PATH: Optional directory containing the account file.
- GOOGLE_SHEET_NAME, GOOGLE_CLOUD_WORKSHEET, GOOGLE_HTC_WORKSHEET: Google Sheets targets.
- ACCOUNTING_SERVER_URL, ACCOUNTING_SCOPE, ACCOUNTING_METRIC, DATE_FROM, DATE_TO: Accounting data configuration.

Run tests

- Use the project's venv or Poetry to run tests. Example:

  ./pyOKR_VOs_CPUs_Accounting/.venv/bin/python -m pytest -q

If you'd like the file to be shorter or in a different location, tell me where
and I will update it.
- ACCOUNTING_SCOPE: Scope of accounting (`cloud` / `htc` etc.).
