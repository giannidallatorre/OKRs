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

def format_reporting_period(env):
    """Safely construct the reporting period string 'YYYY.MM-MM'"""
    date_from = env.get('DATE_FROM')
    date_to = env.get('DATE_TO')
    
    if not date_from or not date_to:
        print(colourise("yellow", "[WARN]"), "DATE_FROM or DATE_TO environment variables are missing.")
        return "UNKNOWN_PERIOD"
        
    try:
        # Expected format: YYYY/MM or YYYY-MM
        # Robustly handle different separators
        df = date_from.replace("/", "-")
        dt = date_to.replace("/", "-")
        
        year = df[0:4]
        start_month = df[-2:]
        end_month = dt[-2:]
        
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
    """Reading profile settings from env"""
    d = {}
    
    # List of all known environment variables across all modules
    keys = [
        # Generic
        'LOG', 'DATE_FROM', 'DATE_TO', 'SSL_CHECK',
        
        # Google / Sheets
        'SERVICE_ACCOUNT_PATH', 'SERVICE_ACCOUNT_FILE', 'GOOGLE_SHEET_NAME',
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
        'LOG': 'INFO',
        'SSL_CHECK': 'True',
        
        # Google Sheet worksheet defaults
        'GOOGLE_CLOUD_WORKSHEET': 'Cloud',
        'GOOGLE_HTC_WORKSHEET': 'HTC',
        'GOOGLE_VOS_WORKSHEET': 'VOs',
        'GOOGLE_VOS_REPORT_WORKSHEET': 'Report',
        'GOOGLE_ORDERS_WORKSHEET': 'Orders',
        'GOOGLE_SLAs_WORKSHEET': 'SLAs',
        'GOOGLE_SLAs_CLOUD_WORKSHEET': 'CloudReport',
        'GOOGLE_SLAs_HTC_WORKSHEET': 'HTCReport',
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
    if 'GOOGLE_SHEET_NAME' in d and ('GOOGLE_SLAs_SHEET_NAME' not in d or not d['GOOGLE_SLAs_SHEET_NAME']):
        d['GOOGLE_SLAs_SHEET_NAME'] = d['GOOGLE_SHEET_NAME']

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
    """Initialize Google credentials from environment"""
    try:
        # Try to load service account from JSON string in environment
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
            print(colourise("red", "[ABORT]"), \
                f"The {spreadsheet_env_var} ({sheet_name}) points to a non-existent sheet")
            return None

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
            print(colourise("red", "[ABORT]"), \
                f"The {worksheet_env_var} setting points to a non-existent worksheet")
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
