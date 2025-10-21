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
