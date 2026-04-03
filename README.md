# EGI OKR Tracking System 📊

Automated accounting and reporting tool for the EGI Foundation to track **Objectives and Key Results (OKRs)**. This system aggregates data from multiple sources (Accounting Portal, Operations Portal, Jira, Confluence) and synchronizes it with Google Sheets.

---

## 🚀 Key Features

*   **Multi-Source Data Aggregation**:
    *   **CPU/h Computing**: Fetches Cloud and HTC consumption via EGI Accounting Portal.
    *   **User Metrics**: Tracks 'Registered', 'Total', and 'Active' users from VO registries.
    *   **Service Orders**: Monitors EOSC Marketplace orders via Jira.
    *   **SLA Compliance**: Syncs finalized SLAs from Confluence and Operations Portal.
    *   **Infrastructure Discovery**: Fetches active FedCloud sites and VM images (templates) via the new Cloud Info API (`is.cloud.egi.eu`).
*   **Intelligent Synchronization**:
    *   **Read-Once, Write-Batch**: High-performance GSheets sync that minimizes API calls.
    *   **Quota Safety**: Built-in batching and defensive delays to avoid `429 Quota Exceeded` errors.
    *   **Historic Backfills**: Utilities to populate multi-year historical data (2020-2025+).
*   **Flexible Execution**:
    *   **Modern CLI**: Powerful Typer-based command line interface.
    *   **Print Mode**: Local testing without GSheets credentials.
    *   **GitHub Actions**: fully automated daily/monthly updates.

---

## 🛠️ Quick Start

### 1. Requirements
*   Python 3.10+
*   Google Service Account (see [Setup Guide](#google-account-setup))
*   API Tokens for EGI Portals (Jira, Operations, Confluence)

### 2. Installation
The recommended way is to set up your local environment using the new generic automation:
```bash
# Clone and enter directory
git clone https://github.com/egi-foundation/okr-accounting.git
cd okr-accounting

# Automatically create the virtual environment and install all dependencies
make setup

# Activate the virtual environment
source venv/bin/activate
```

### 3. Basic Execution
Run a dry-run to verify your connection and see results in your terminal:
```bash
# Check Cloud CPUs
egi-okr cpus --print --scope cloud

# Check everything for a specific period
egi-okr all --print --date-from 2024/01 --date-to 2024/03
```

---

## 🕹️ CLI Reference

The `egi-okr` command is your main entry point.

| Command | Description |
| :--- | :--- |
| `cpus` | Compute accounting (Scope: `cloud` or `htc`) |
| `slas` | Service Level Agreement accounting |
| `users` | User statistics and membership reports |
| `orders` | Marketplace Service Orders |
| `templates` | Fetch VM images/templates from Cloud Info API |
| `all` | Sequentially run all modules |

### Common Flags
*   `--print`: Terminal-only mode (No GSheets credentials required). Bypasses strict quarter validation.
*   `--insecure`: Bypasses SSL issues (Required for some macOS installations).
*   `--date-from` / `--date-to`: Specify reporting YYYY/MM period. Google Sheets syncing strictly enforces **full quarters** (e.g., `2024/01` to `2024/03`). If omitted, it automatically defaults to the last fully completed quarter.

---

## ⚙️ Configuration & Secrets

### Environment Variables (.env)
Create a `.env` file for local persistence:
```env
# API Access
JIRA_AUTH_TOKEN=your_token
OPERATIONS_API_KEY=your_key
CONFLUENCE_AUTH_TOKEN=your_pat
SERVICE_ACCOUNT_FILE=credentials.json

# Preferences
PRINT_MODE=True
SSL_CHECK=False
GOOGLE_SHEET_NAME=EGI_OKR_Reporting
GOOGLE_SHARE_EMAILS=user1@example.com,user2@example.com
```

### GitHub Actions
For automated production runs, configure these **Repository Secrets**:
1.  `SERVICE_ACCOUNT_JSON`: Full content of your Google JSON key.
2.  `JIRA_AUTH_TOKEN`, `OPERATIONS_API_KEY`, `CONFLUENCE_AUTH_TOKEN`.
3.  `GOOGLE_SHEET_NAME`: The name of your production spreadsheet.
4.  `GOOGLE_SHARE_EMAILS`: (Optional) Comma-separated list of emails to automatically share newly created sheets with.

---

## �️ Troubleshooting

### SSL: CERTIFICATE_VERIFY_FAILED (macOS)

If you encounter an SSL verification error on macOS, it's usually because Python doesn't have its own certificate store.

**Fix 1: Permanent (Recommended)**
Open your Applications folder, find the Python version you are using (e.g., Python 3.13), and double-click the `Install Certificates.command` file. This will install the necessary root certificates.

**Fix 2: Quick Bypass**
Use the `--insecure` flag in the CLI:
```bash
egi-okr cpus --print --insecure
```

---

## �📖 Detailed Setup Guides

<details>
<summary><b>Google Account Setup</b> (Click to expand)</summary>

1.  Head to [Google Cloud Console](https://console.cloud.google.com/).
2.  Enable **Google Drive API** & **Google Sheets API**.
3.  Create a **Service Account** and download its **JSON Key**.
4.  Rename it to `credentials.json` in your local project root.
5.  **Critical**: Open your Google Sheet and "Share" it with the email address of the Service Account (found in the JSON).
</details>

<details>
<summary><b>EGI Portal tokens</b> (Click to expand)</summary>

*   **Jira**: [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens).
*   **Operations Portal**: [API Documentation](https://operations-portal.egi.eu/api-documentation).
*   **Confluence (IMS)**: [Personal Access Tokens](https://confluence.egi.eu/plugins/personalaccesstokens/usertokens.action).
</details>

<details>
<summary><b>Historical Backfills</b> (Click to expand)</summary>

Populate years of data in minutes:
```bash
# Quarterly backfill from 2020 to 2026
make backfill ARGS="--start 2020 --end 2026"
```
</details>

---

## 🧪 Testing & Quality

*   **Unit Tests**: `make test-unit`
*   **CLI Tests**: `make test-cli`
*   **CI Simulations**: `make test-act` (requires [act](https://github.com/nektos/act))

---

## 🔗 References

*   [EGI Accounting Portal](https://accounting.egi.eu/)
*   [gspread Documentation](https://docs.gspread.org/)
*   [EGI IMS Space](https://confluence.egi.eu/display/IMS)
