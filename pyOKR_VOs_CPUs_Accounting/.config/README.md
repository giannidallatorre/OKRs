# Local config and service account

This directory contains local configuration files used by the project. It is intentionally excluded from version control to avoid committing secrets (see repository `.gitignore`).

If you need to run the project locally, create a Google service account JSON file and place it here as `service_account.json`.

DO NOT commit your `service_account.json` to Git. Follow the steps below to create it safely from a template.

## Create `service_account.json` from the template

1. Make a copy of the template included in the repository:

   cp service_account.json.template service_account.json

2. Edit `service_account.json` and fill in any required fields if the template is partial. Typically you will download a full JSON from the Google Cloud Console and place it directly in this path instead of editing the template.

3. Verify the file is present and accessible by your environment variables or the project config:

   export SERVICE_ACCOUNT_PATH=$(pwd)
   export SERVICE_ACCOUNT_FILE=${SERVICE_ACCOUNT_PATH}/service_account.json

4. Run the application or tests that require the service account. The project `.gitignore` already prevents `service_account.json` from being committed.

## Regenerating the file

If you accidentally committed credentials, do not push them. Remove them from Git history and rotate the credentials in Google Cloud.

## Troubleshooting

- If the application reports `Service account file not found`, check `SERVICE_ACCOUNT_FILE` and file permissions.
- If authentication fails, download a fresh JSON key from the Google Cloud Console and replace `service_account.json`.
