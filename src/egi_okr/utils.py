#!/usr/bin/env python3
#
#  Copyright 2024 EGI Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import json
import warnings
import gspread
import traceback

# Suppress warnings
warnings.filterwarnings("ignore")

def validate_date_format(date_str, field_name='DATE'):
    """
    Validate date string format is YYYY/MM or YYYY-MM.
    Returns (valid: bool, normalized: str, error: str)
    """
    if not date_str:
        return False, None, f"{field_name} is empty"
    
    # Normalize to YYYY/MM format
    normalized = date_str.replace("-", "/")
    
    # Validate format
    parts = normalized.split("/")
    if len(parts) != 2:
        return False, None, f"{field_name} '{date_str}' invalid format (expected YYYY/MM or YYYY-MM)"
    
    try:
        year, month = parts
        if not (year.isdigit() and len(year) == 4):
            return False, None, f"{field_name} year must be 4 digits, got '{year}'"
        if not (month.isdigit() and len(month) == 2):
            return False, None, f"{field_name} month must be 2 digits, got '{month}'"
        
        month_int = int(month)
        if not (1 <= month_int <= 12):
            return False, None, f"{field_name} month must be 01-12, got '{month}'"
        
        return True, normalized, None
    except Exception as e:
        return False, None, f"{field_name} validation error: {str(e)}"

def format_reporting_period(env):
    """Safely construct the reporting period string 'YYYY.MM-MM'"""
    date_from = env.get('DATE_FROM')
    date_to = env.get('DATE_TO')
    
    if not date_from or not date_to:
        # Fallback to last month if not provided
        try:
            import datetime
            from dateutil.relativedelta import relativedelta
            last_month = datetime.date.today() - relativedelta(months=1)
            date_from = date_from or last_month.strftime("%Y/%m")
            date_to = date_to or last_month.strftime("%Y/%m")
            # Update the environment dict so other modules can use these calculated dates
            env['DATE_FROM'] = date_from
            env['DATE_TO'] = date_to
        except Exception as e:
            print(colourise("yellow", "[WARN]"), f"Failed to calculate default dates: {e}")
            return "UNKNOWN_PERIOD"
    
    # Validate DATE_FROM format
    valid_from, norm_from, err_from = validate_date_format(date_from, 'DATE_FROM')
    if not valid_from:
        print(colourise("red", "[ERROR]"), err_from)
        return "INVALID_PERIOD"
    
    # Validate DATE_TO format
    valid_to, norm_to, err_to = validate_date_format(date_to, 'DATE_TO')
    if not valid_to:
        print(colourise("red", "[ERROR]"), err_to)
        return "INVALID_PERIOD"
    
    try:
        # Use normalized format (YYYY/MM)
        parts_from = norm_from.split("/")
        parts_to = norm_to.split("/")
        
        year = parts_from[0]
        start_month = parts_from[1]
        end_month = parts_to[1]
        
        return f"{year}.{start_month}-{end_month}"
    except Exception as e:
        print(colourise("yellow", "[WARN]"), f"Error formatting reporting period: {e}")
        return "INVALID_PERIOD"

def colourise(colour, text):
    """Colourise - colours text in shell."""
    if colour == "black":
        return "\033[1;30m" + str(text) + "\033[1;m"
    if colour == "red":
        return "\033[1;31m" + str(text) + "\033[1;m"
    if colour == "green":
        return "\033[1;32m" + str(text) + "\033[1;m"
    if colour == "yellow":
        return "\033[1;33m" + str(text) + "\033[1;m"
    if colour == "blue":
        return "\033[1;34m" + str(text) + "\033[1;m"
    if colour == "magenta":
        return "\033[1;35m" + str(text) + "\033[1;m"
    if colour == "cyan":
        return "\033[1;36m" + str(text) + "\033[1;m"
    if colour == "gray":
        return "\033[1;37m" + str(text) + "\033[1;m"
    return str(text)

def highlight(colour, text):
    """Highlight - highlights text in shell."""
    if colour == "black":
        return "\033[1;40m" + str(text) + "\033[1;m"
    if colour == "red":
        return "\033[1;41m" + str(text) + "\033[1;m"
    if colour == "green":
        return "\033[1;42m" + str(text) + "\033[1;m"
    if colour == "yellow":
        return "\033[1;43m" + str(text) + "\033[1;m"
    if colour == "blue":
        return "\033[1;44m" + str(text) + "\033[1;m"
    if colour == "magenta":
        return "\033[1;45m" + str(text) + "\033[1;m"
    if colour == "cyan":
        return "\033[1;46m" + str(text) + "\033[1;m"
    if colour == "gray":
        return "\033[1;47m" + str(text) + "\033[1;m"
    return str(text)

def find_difference(activeVOs_1, activeVOs_2):
    ''' Find difference between two comma-separated strings '''

    set_1 = set(activeVOs_1.split(", ")) if activeVOs_1 else set()
    set_2 = set(activeVOs_2.split(", ")) if activeVOs_2 else set()

    arrivingVOs = set_2 - set_1
    leavingVOs = set_1 - set_2

    arrivingVOs_str = ', '.join(arrivingVOs) if arrivingVOs else "-"
    leavingVOs_str = ', '.join(leavingVOs) if leavingVOs else "-"

    return arrivingVOs_str, leavingVOs_str

def get_env_settings():
    """
    Retrieve environment configuration with three-level precedence:
    
    Level 1 (Hardcoded Defaults): Production-standard values for all services.
                                   Ensures out-of-the-box functionality.
    Level 2 (Environment Variables): Override defaults from OS environment.
                                     Supports GitHub Actions secrets and local overrides.
    Level 3 (Cascading Defaults): Derive values from other settings if not explicitly set.
                                   Examples: JIRA_PROJECT cascades to projectkeys,
                                   GOOGLE_SHEET_NAME cascades to SLAs sheet name.
    
    Cascading Rules:
      - JIRA_PROJECT → SERVICE_ORDERS_PROJECTKEY, COMPLAINS_PROJECTKEY, VIOLATIONS_PROJECTKEY
      - GOOGLE_SHEET_NAME → GOOGLE_SLAs_SHEET_NAME (if SLAs sheet is same as main sheet)
      - Missing DATE_FROM/DATE_TO → Calculated as last month
    
    Returns:
        dict: Complete configuration with all required environment variables
    """
    d = {}
    
    # List of all known environment variables across all modules
    keys = [
        # Generic
        'LOG', 'DATE_FROM', 'DATE_TO', 'SSL_CHECK', 'USER_EMAIL',
        
        # Google / Sheets
        'SERVICE_ACCOUNT_PATH', 'SERVICE_ACCOUNT_FILE', 'SERVICE_ACCOUNT_JSON', 'GOOGLE_SHEET_NAME',
        'GOOGLE_SERVICE_ORDERS_WORKSHEET', 'GOOGLE_VOS_WORKSHEET', 'GOOGLE_VOS_REPORT_WORKSHEET',
        'GOOGLE_ORDERS_WORKSHEET',
        'GOOGLE_SLAs_CLOUD_WORKSHEET', 'GOOGLE_SLAs_HTC_WORKSHEET',
        'GOOGLE_CLOUD_WORKSHEET', 'GOOGLE_HTC_WORKSHEET',
        'GOOGLE_SLAs_SHEET_NAME', 'GOOGLE_SLAs_WORKSHEET', 'GOOGLE_OLAs_WORKSHEET',
        'ACTIVE_SLAs_FILE',

        # Jira
        'JIRA_SERVER_URL', 'JIRA_AUTH_TOKEN', 'JIRA_PROJECT',
        'SERVICE_ORDERS_PROJECTKEY', 'SERVICE_ORDERS_ISSUETYPE',
        'COMPLAINS_PROJECTKEY', 'VIOLATIONS_PROJECTKEY', 'ISSUETYPE',

        # Operations Portal
        'OPERATIONS_SERVER_URL', 'OPERATIONS_API_KEY', 'OPERATIONS_FORMAT',
        'OPERATIONS_VO_LIST_PREFIX', 'OPERATIONS_VO_ID_CARD_PREFIX', 'OPERATIONS_VOS_REPORT_PREFIX',

        # Accounting Portal
        'ACCOUNTING_SERVER_URL', 'ACCOUNTING_SCOPE', 'ACCOUNTING_METRIC',
        'ACCOUNTING_LOCAL_JOB_SELECTOR', 'ACCOUNTING_VO_GROUP_SELECTOR', 'ACCOUNTING_DATA_SELECTOR',

        # EGI Check-in OAuth2
        'CHECKIN_TOKEN_ENDPOINT', 'CHECKIN_REFRESH_TOKEN', 'CHECKIN_CLIENT_ID', 'CHECKIN_CLIENT_SECRET'
    ]

    # Define production-standard defaults
    defaults = {
        'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
        'ACCOUNTING_SCOPE': 'cloud',
        'ACCOUNTING_METRIC': 'sum_elap_processors',
        'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
        'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
        'ACCOUNTING_DATA_SELECTOR': 'JSON',
        'OPERATIONS_SERVER_URL': 'https://operations-portal.egi.eu/api',
        'OPERATIONS_FORMAT': 'json',
        'OPERATIONS_VO_LIST_PREFIX': '/vo-list',
        'OPERATIONS_VO_ID_CARD_PREFIX': '/vo-id-card',
        'OPERATIONS_VOS_REPORT_PREFIX': '/vo-report',
        'JIRA_SERVER_URL': 'https://jira.egi.eu/',
        'JIRA_PROJECT': 'EOSC',
        'SERVICE_ORDERS_PROJECTKEY': 'EGISO',
        'SERVICE_ORDERS_ISSUETYPE': 'Service Order',
        'COMPLAINS_PROJECTKEY': 'IMSCC',
        'VIOLATIONS_PROJECTKEY': 'IMSSLA',
        'ISSUETYPE': 'Service SLA Violation',
        'LOG': 'INFO',
        'SSL_CHECK': 'True',
        'SERVICE_ACCOUNT_FILE': '.config/service_account.json',
        
        # Google Sheet defaults
        'GOOGLE_SHEET_NAME': 'EGI_OKR_Test_Verify',
        'GOOGLE_SLAs_SHEET_NAME': 'EGI_OKR_Test_Verify',
        'GOOGLE_CLOUD_WORKSHEET': 'Cloud',
        'GOOGLE_HTC_WORKSHEET': 'HTC',
        'GOOGLE_VOS_WORKSHEET': 'VOs',
        'GOOGLE_VOS_REPORT_WORKSHEET': 'Report',
        'GOOGLE_ORDERS_WORKSHEET': 'Orders',
        'GOOGLE_SLAs_WORKSHEET': 'SLAs',
        'GOOGLE_SLAs_CLOUD_WORKSHEET': 'CloudReport',
        'GOOGLE_SLAs_HTC_WORKSHEET': 'HTCReport',
        'GOOGLE_OLAs_WORKSHEET': 'OLAs',
        'ACTIVE_SLAs_FILE': 'active_slas.json'
    }

    # Populate with defaults first
    d.update(defaults)

    for key in keys:
        val = os.environ.get(key)
        if val: # Only override if the environment variable is not None AND not empty
            d[key] = val
    
    # Cascade JIRA_PROJECT to specific keys if they are missing
    if 'JIRA_PROJECT' in d:
        for key in ['SERVICE_ORDERS_PROJECTKEY', 'COMPLAINS_PROJECTKEY', 'VIOLATIONS_PROJECTKEY']:
            if key not in d or not d[key] or d.get(key) == defaults.get(key):
                 d[key] = d['JIRA_PROJECT']

    # Fallback for GOOGLE_SLAs_SHEET_NAME
    # If not set by environment, use GOOGLE_SHEET_NAME
    if not d.get('GOOGLE_SLAs_SHEET_NAME'):
        d['GOOGLE_SLAs_SHEET_NAME'] = d.get('GOOGLE_SHEET_NAME')

    return d

def validate_google_credentials(service_info):
    """Validate Google service account credentials"""
    try:
        if not service_info.get('client_email'):
            print(colourise("red", "[ABORT]"), \
                "Missing client_email in service account credentials")
            return False

        if not service_info.get('private_key'):
            print(colourise("red", "[ABORT]"), \
                "Missing private_key in service account credentials")
            return False

        # Basic format validation for client_email
        if not '@' in service_info['client_email'] or \
           not service_info['client_email'].endswith('.gserviceaccount.com'):
            print(colourise("red", "[ABORT]"), \
                "Invalid client_email format in service account credentials")
            return False

        # Basic format validation for private_key
        if not service_info['private_key'].startswith('-----BEGIN PRIVATE KEY-----') or \
           not service_info['private_key'].strip().endswith('-----END PRIVATE KEY-----'):
                 print(colourise("red", "[ABORT]"), \
                    "Invalid private_key format in service account credentials")
                 return False

        return True
    except Exception as e:
        print(colourise("red", "[ABORT]"), \
            f"Error validating credentials: {e}")
        return False

def init_google_credentials(env):
    """
    Initialize Google credentials from environment with two-mode support.
    
    Service Account Configuration Modes:
    
    1. SERVICE_ACCOUNT_JSON (GitHub Actions mode):
       - String: Full service account JSON as environment variable
       - Use case: GitHub Actions secrets (large JSON in one secret)
       - Example: export SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
    
    2. SERVICE_ACCOUNT_FILE (Local development mode):
       - File path: Location of service_account.json file
       - Default: .config/service_account.json
       - Use case: Local testing with act or pytest
       - Example: .config/service_account.json (created from template)
    
    Precedence: SERVICE_ACCOUNT_JSON is checked first (GitHub Actions),
               then falls back to SERVICE_ACCOUNT_FILE (local).
    """
    try:
        # Try to load service account from JSON string in environment
        # (GitHub Actions - secrets passed as JSON strings)
        if 'SERVICE_ACCOUNT_JSON' in env:
            try:
                service_info = json.loads(env['SERVICE_ACCOUNT_JSON'])
                if not validate_google_credentials(service_info):
                    return None
                return gspread.service_account_from_dict(service_info)
            except json.JSONDecodeError:
                print(colourise("red", "[ABORT]"), \
                    "Invalid SERVICE_ACCOUNT_JSON content")
                return None
            except gspread.exceptions.GSpreadException as e:
                print(colourise("red", "[ABORT]"), \
                    f"Error loading service account from JSON: {e}")
                return None

        # Fallback to file-based service account
        # (Local development - .config/service_account.json)
        elif 'SERVICE_ACCOUNT_FILE' in env:
            try:
                with open(env['SERVICE_ACCOUNT_FILE']) as f:
                    service_info = json.load(f)
                    if not validate_google_credentials(service_info):
                        return None
                return gspread.service_account(env['SERVICE_ACCOUNT_FILE'])
            except FileNotFoundError:
                print(colourise("red", "[ABORT]"), \
                    "SERVICE_ACCOUNT_FILE not found")
                return None
            except json.JSONDecodeError:
                print(colourise("red", "[ABORT]"), \
                    "Invalid JSON in SERVICE_ACCOUNT_FILE")
                return None
            except gspread.exceptions.GSpreadException as e:
                print(colourise("red", "[ABORT]"), \
                    f"Error loading service account from file: {e}")
                return None

        else:
            print(colourise("red", "[ABORT]"), \
                "No service account credentials found")
            return None

    except Exception as e:
        print(colourise("red", "[ABORT]"), \
            f"Unexpected error initializing credentials: {e}")
        return None

def validate_spreadsheet_access(account, env):
    """Validate access to the Google Spreadsheet"""
    try:
        # List spreadsheets to verify API access
        spreadsheets = account.list_spreadsheet_files()
        if not spreadsheets:
            print(colourise("yellow", "[WARN]"), \
                "No spreadsheets accessible to this service account")
            
        # Check if target spreadsheet is accessible
        target_sheet = env.get('GOOGLE_SHEET_NAME')
        if not target_sheet:
             return False

        accessible_sheets = [s['name'] for s in spreadsheets]
        if target_sheet not in accessible_sheets:
            print(colourise("red", "[ABORT]"), \
                f"Service account cannot access sheet '{target_sheet}'. " \
                "Ensure the sheet is shared with the service account email.")
            return False
            
        return True
    except gspread.exceptions.APIError as e:
        print(colourise("red", "[ABORT]"), \
            f"Google Sheets API error: {e}")
        return False
    except Exception as e:
        print(colourise("red", "[ABORT]"), \
            f"Error validating spreadsheet access: {e}")
        return False

def init_GWorkSheet(env, worksheet_env_var, spreadsheet_env_var='GOOGLE_SHEET_NAME'):
    """Initialize the GWorkSheet settings and return the worksheet"""
    try:
        # Get the service account
        account = init_google_credentials(env)
        if not account:
            return None

        # Open the GoogleSheet
        try:
            sheet_name = env.get(spreadsheet_env_var)
            if not sheet_name:
                 print(colourise("red", "[ABORT]"), f"{spreadsheet_env_var} environment variable not set")
                 return None
            sheet = account.open(sheet_name)
            print(colourise("cyan", "[INFO]"), f"Connected to Spreadsheet: '{sheet.title}'")
            print(colourise("cyan", "[INFO]"), f"URL: {sheet.url}")
        except gspread.exceptions.SpreadsheetNotFound:
            print(colourise("yellow", "[WARN]"), \
                f"The spreadsheet '{sheet_name}' was not found.")
            
            try:
                print(colourise("cyan", "[INFO]"), f"Creating new spreadsheet: '{sheet_name}'...")
                sheet = account.create(sheet_name)
                print(colourise("green", "[SUCCESS]"), f"Created spreadsheet: '{sheet.title}'")
                print(colourise("green", "[INFO]"), f"URL: {sheet.url}")
            except Exception as e:
                print(colourise("red", "[ABORT]"), f"Failed to create spreadsheet: {e}")
                return None

        # Check permissions and share with user if needed
        # This runs for both existing and newly created sheets
        user_email = env.get('USER_EMAIL')
        if user_email:
            try:
                # Blindly attempt to share - gspread handles 'already exists' gracefully usually,
                # or we catch the exception. More efficient than listing permissions which requires Owner role.
                # Actually, Service Account IS Owner if it created it.
                # If SA is just an editor (Production sheet), this might fail if it can't share.
                # But for Test sheet (created by SA), it works.
                print(colourise("cyan", "[INFO]"), f"Ensuring access for {user_email}...")
                sheet.share(user_email, perm_type='user', role='writer')
                print(colourise("green", "[SUCCESS]"), f"Shared with {user_email} (or already shared).")
            except Exception as e:
                # Don't abort if sharing fails (might be Prod sheet owned by someone else)
                print(colourise("yellow", "[WARN]"), f"Could not share spreadsheet: {e}")
        else:
             if account.auth.service_account_email:
                 print(colourise("yellow", "[INFO]"), f"Sheet owned/accessed by: {account.auth.service_account_email}")
             # If we are here, we probably didn't create it (since that returns None on fail),
             # and we failed to share it (or didn't try).
             # We should NOT return None here, because the sheet WAS found/opened successfully above.
             # We only log the sharing status.
             pass

        # Opening the sheet validates access. If it fails, common errors are handled.
        
        # Open the Worksheet
        try:
            if worksheet_env_var not in env:
                 print(colourise("red", "[ABORT]"), f"{worksheet_env_var} environment variable not set")
                 return None
                 
            worksheet_name = env[worksheet_env_var]
            worksheet = sheet.worksheet(worksheet_name)
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            print(colourise("yellow", "[WARN]"), \
                f"The worksheet '{worksheet_name}' was not found.")
            
            try:
                print(colourise("cyan", "[INFO]"), f"Creating new worksheet: '{worksheet_name}'...")
                # Create worksheet with sensible default dimensions (enough columns for reports)
                worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=20)
                print(colourise("green", "[SUCCESS]"), f"Created worksheet: '{worksheet.title}'")
                return worksheet
                
            except Exception as e:
                print(colourise("red", "[ABORT]"), f"Failed to create worksheet: {e}")
                return None

    except Exception as e:
        print(colourise("red", "[ABORT]"), \
            f"Unexpected error: {e}")
        return None

def handle_exception(e, env, worksheet=None):
    ''' Handle exceptions and print detailed error messages '''
    # Simple logging if logging not configured or just use print/logging
    import logging
    logging.error(f"ERROR: {e}")
    if worksheet:
        try:
            logging.error(f"Spreadsheet: {worksheet.spreadsheet.title}")
            logging.error(f"Worksheet: {worksheet.title}")
        except:
            pass
    logging.error("Please ensure that the header row in the worksheet is unique.")
    logging.error("Check for duplicate column headers and make sure each header is unique.")
    
    if logging.getLogger().level == logging.DEBUG:
        logging.debug("\n[DEBUG] Traceback:")
        logging.debug(traceback.format_exc())

def get_checkin_access_token(env):
    """Obtain an access token using a refresh token from EGI Check-in."""
    refresh_token = env.get('CHECKIN_REFRESH_TOKEN')
    client_id = env.get('CHECKIN_CLIENT_ID')
    client_secret = env.get('CHECKIN_CLIENT_SECRET')
    token_endpoint = env.get('CHECKIN_TOKEN_ENDPOINT', 'https://aai.egi.eu/oidc/token')

    if not refresh_token or not client_id:
        return None

    payload = {
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': 'openid profile email offline_access'
    }
    if client_secret:
        payload['client_secret'] = client_secret

    try:
        response = requests.post(token_endpoint, data=payload)
        response.raise_for_status()
        return response.json().get('access_token')
    except Exception as e:
        print(colourise("red", "[ERROR]"), f"Failed to refresh Check-in token: {e}")
        return None
