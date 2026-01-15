# Local GitHub Actions Testing

Test GitHub Actions workflows locally using [act](https://github.com/nektos/act).

## Quick Start

1. Install requirements:
   - [act](https://github.com/nektos/act)
   - Docker

2. Setup service account:

   ```bash
   mkdir -p .config
   cp .config/service_account.json.template .config/service_account.json
   # Edit .config/service_account.json with real credentials
   ```

3. Run workflow:

   ```bash
   ./act_setup/run_update_sheet.sh          # Normal mode
   DEBUG=true ./act_setup/run_update_sheet.sh  # Debug mode
   ```

## Notes

- `.config/service_account.json` is required for authentication
- Test credentials are used if no service account is found
- Use DEBUG=true for troubleshooting
