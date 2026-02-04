# Local GitHub Actions Testing

Test GitHub Actions workflows locally using [act](https://github.com/nektos/act).

## Quick Start

1.  **Install Requirements**:
    *   [act](https://github.com/nektos/act)
    *   Docker

2.  **Configure Secrets**:
    Create `act_setup/local.secrets` with your credentials:
    ```bash
    JIRA_AUTH_TOKEN= your_token
    OPERATIONS_API_KEY= your_key
    CHECKIN_REFRESH_TOKEN= your_token
    SERVICE_ACCOUNT_JSON= {"type": "service_account", ...json content...}
    # Optional: Override spreadsheet for local testing
    GOOGLE_SHEET_NAME= EGI_OKR_Test_Verify
    ```

3.  **Run Workflow**:
    ```bash
    ./act_setup/run_update_sheet.sh
    # or via make
    make test-act
    ```

## Notes
*   The script uses `local.secrets` to populate GitHub Secrets.
*   `SERVICE_ACCOUNT_JSON` should be a single-line JSON string.
*   The `.config/` directory is automatically handled by the workflow/act.
