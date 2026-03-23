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
import requests
import gspread
import traceback

# Suppress warnings
warnings.filterwarnings("ignore")

# In-memory cache for connection logging to avoid redundant prints within the same process
_PRINTED_CONNECTIONS = set()

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
    try:
        from dotenv import load_dotenv
        load_dotenv()
        # Fallback to local.secrets if it exists
        local_secrets = os.path.join(os.getcwd(), 'act_setup', 'local.secrets')
        if os.path.exists(local_secrets):
            load_dotenv(dotenv_path=local_secrets)
    except ImportError:
        pass

    d = {}
    
    # List of all known environment variables across all modules
    keys = [
        # Generic
        'LOG', 'DATE_FROM', 'DATE_TO', 'SSL_CHECK', 'USER_EMAIL',
        
        # Google / Sheets
        'SERVICE_ACCOUNT_PATH', 'SERVICE_ACCOUNT_FILE', 'SERVICE_ACCOUNT_JSON', 'GOOGLE_SHEET_NAME',
        'GOOGLE_SERVICE_ORDERS_WORKSHEET', 'GOOGLE_VOS_WORKSHEET', 'GOOGLE_VOS_REGISTERED_WORKSHEET', 'GOOGLE_VOS_TOTAL_WORKSHEET', 'GOOGLE_VOS_REPORT_WORKSHEET',
        'GOOGLE_ORDERS_WORKSHEET',
        'GOOGLE_SLAs_CLOUD_WORKSHEET', 'GOOGLE_SLAs_HTC_WORKSHEET',
        'GOOGLE_TEMPLATES_WORKSHEET',
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
        'ACCOUNTING_LOCAL_JOB_SELECTOR', 'ACCOUNTING_VO_GROUP_SELECTOR', 'ACCOUNTING_BENCHMARK_SELECTOR', 'ACCOUNTING_DATA_SELECTOR',

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
        'ACCOUNTING_BENCHMARK_SELECTOR': 'hepspec06',
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
        'GOOGLE_VOS_WORKSHEET': 'VOs-ActiveUsers',
        'GOOGLE_VOS_REGISTERED_WORKSHEET': 'VOs-RegisteredMembers',
        'GOOGLE_VOS_TOTAL_WORKSHEET': 'VOs-TotalMembers',
        'GOOGLE_VOS_REPORT_WORKSHEET': 'Report',
        'GOOGLE_ORDERS_WORKSHEET': 'Orders',
        'GOOGLE_SLAs_WORKSHEET': 'SLAs',
        'GOOGLE_SLAs_CLOUD_WORKSHEET': 'CloudReport',
        'GOOGLE_SLAs_HTC_WORKSHEET': 'HTCReport',
        'GOOGLE_OLAs_WORKSHEET': 'OLAs',
        'GOOGLE_TEMPLATES_WORKSHEET': 'Templates',
        'ACTIVE_SLAs_FILE': 'active_slas.json'
    }

    # Populate with defaults first
    d.update(defaults)

    for key in keys:
        val = os.environ.get(key)
        if val: # Only override if the environment variable is not None AND not empty
            d[key] = val
    
    # Cascade JIRA_PROJECT to specific keys if targets are missing OR default
    # but ONLY if JIRA_PROJECT itself is not default or was explicitly provided.
    if d.get('JIRA_PROJECT') != defaults.get('JIRA_PROJECT') or \
       'JIRA_PROJECT' in os.environ:
        for key in ['SERVICE_ORDERS_PROJECTKEY', 'COMPLAINS_PROJECTKEY', 'VIOLATIONS_PROJECTKEY']:
            if key not in d or not d[key] or d.get(key) == defaults.get(key):
                 d[key] = d['JIRA_PROJECT']

    # Fallback for GOOGLE_SLAs_SHEET_NAME
    # Precedence: Explicit ENV > GOOGLE_SHEET_NAME (if set) > Default
    if not os.environ.get('GOOGLE_SLAs_SHEET_NAME'):
        if d.get('GOOGLE_SHEET_NAME') and d.get('GOOGLE_SHEET_NAME') != defaults.get('GOOGLE_SHEET_NAME'):
             d['GOOGLE_SLAs_SHEET_NAME'] = d['GOOGLE_SHEET_NAME']

    return d

def get_sla_vos_list(env):
    """
    Retrieve the list of VOs that have or had SLAs.
    
    This list is used to query accounting data for all these VOs.
    Future work can add API integration to dynamically determine and filter only active SLAs.
    
    Precedence:
    1. SLA_VOs_LIST environment variable (comma-separated list of VO names)
    2. active_slas.json file (if exists - JSON with "vos" key)
    3. Default hardcoded list
    
    Returns:
        list: List of VO names to query for SLA accounting data
    """
    # Default list of all VOs that have or had SLAs
    default_sla_vos = [
        'belle', 'biomed', 'eiscat.se', 'enmr.eu', 'fusion', 'icecube', 
        'openrisknet.org', 'perla-pv.ro', 'vo.ai4publicpolicy.eu', 'vo.clarin.eu', 
        'vo.decido-project.eu', 'vo.digitbrain.eu', 'vo.emphasisproject.eu', 
        'vo.emso-eric.eu', 'vo.enes.org', 'vo.envrihub.eu', 'vo.eries.eu', 
        'vo.eurosea.marine.ie', 'vo.geoss.eu', 'vo.imagine-ai.eu', 'vo.lethe-project.eu', 
        'vo.nbis.se', 'vo.obsea.es', 'vo.neurodesk.eu', 'vo.operas-eu.org', 
        'vo.oipub.com', 'vo.pangeo.eu', 'vo.radiotracers4psma.eu', 'vo.usegalaxy.eu', 
        'vo.access.egi.eu', 'training.egi.eu', 'vo.seadatanet.org', 'vo.nextgeoss.eu', 
        'vo.aneris.eu', 'vo.epos-eric.eu', 'vo.openbiomaps.org'
    ]
    
    # 1. Check environment variable first
    if os.environ.get('SLA_VOs_LIST'):
        vo_str = os.environ.get('SLA_VOs_LIST')
        return [vo.strip() for vo in vo_str.split(',') if vo.strip()]
    
    # 2. Try to load from .config/sla_vos.json file
    sla_vos_file = env.get('SLA_VOs_FILE', '.config/sla_vos.json')
    if os.path.exists(sla_vos_file):
        try:
            with open(sla_vos_file, 'r') as f:
                data = json.load(f)
                # Support either a list or a dict with 'vos' key
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'vos' in data:
                    return data['vos']
        except Exception as e:
            print(colourise("yellow", "[WARN]"), f"Failed to read {sla_vos_file}: {e}")
    
    # 3. Use default list
    return default_sla_vos

def initialize_slas_sheet(worksheet, env):
    """Initialize the SLAs reference sheet with a list of VOs that have or had SLAs.
    
    Simple structure:
    - Column A: VO Name
    - Remaining columns: For future use (status, notes, etc.)
    
    Args:
        worksheet: The gspread worksheet to populate
        env: Environment configuration
    """
    try:
        # Check if sheet already has data
        existing = worksheet.get_all_values()
        if existing and len(existing) > 1:
            print(colourise("cyan", "[INFO]"), "SLAs sheet already populated, skipping initialization")
            return
        
        sla_vos = get_sla_vos_list(env)
        if not sla_vos:
            print(colourise("yellow", "[WARN]"), "No SLA VOs to initialize")
            return
        
        # Build rows: header + VO names
        rows_to_insert = [['VO Name']]
        for vo in sla_vos:
            rows_to_insert.append([vo])
        
        # Write all rows
        print(colourise("cyan", "[INFO]"), f"Initializing SLAs sheet with {len(sla_vos)} VOs...")
        worksheet.update('A1:A' + str(len(rows_to_insert)), rows_to_insert, value_input_option='RAW')
        print(colourise("green", "[SUCCESS]"), f"SLAs sheet initialized with {len(sla_vos)} VOs")
        
    except Exception as e:
        print(colourise("yellow", "[WARN]"), f"Failed to initialize SLAs sheet: {e}")

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
    """
    # Connection reuse: return cached client if available
    if env.get('_gspread_account'):
        return env.get('_gspread_account')

    try:
        # Try to load service account from JSON string in environment
        # (GitHub Actions - secrets passed as JSON strings)
        if 'SERVICE_ACCOUNT_JSON' in env:
            try:
                service_info = json.loads(env['SERVICE_ACCOUNT_JSON'])
                if not validate_google_credentials(service_info):
                    return None
                account = gspread.service_account_from_dict(service_info)
                env['_gspread_account'] = account
                return account
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
                account = gspread.service_account(env['SERVICE_ACCOUNT_FILE'])
                env['_gspread_account'] = account
                return account
            except FileNotFoundError:
                print(colourise("red", "[ABORT]"), \
                    "SERVICE_ACCOUNT_FILE not found. " + \
                    colourise("yellow", "(Hint: Use --print to test without Google Sheets)"))
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

_CACHE_FILE = ".okr_conn_cache.json"

def _load_process_cache():
    """Load connection and sharing cache from local file (persists across CI steps)."""
    import os
    import json
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, 'r') as f:
                return json.load(f)
        except: pass # Ignore errors, return default empty cache
    return {"connections": {}, "shared": []}

def _save_process_cache(cache):
    """Save connection and sharing cache to local file."""
    import os
    import json
    try:
        with open(_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except: pass # Ignore errors, cache is not critical

def init_GWorkSheet(env, worksheet_env_var, spreadsheet_env_var='GOOGLE_SHEET_NAME'):
    """Initialize the GWorkSheet settings and return the worksheet"""
    try:
        # Get the service account
        account = init_google_credentials(env)
        if not account:
            return None

        # Open the GoogleSheet
        just_created = False
        cache = _load_process_cache()
        connections = cache.get("connections", {})
        shared = set(cache.get("shared", []))

        try:
            sheet_name = env.get(spreadsheet_env_var)
            if not sheet_name:
                 print(colourise("red", "[ABORT]"), f"{spreadsheet_env_var} environment variable not set. " + \
                       colourise("yellow", "(Hint: Use --print to test without Google Sheets)"))
                 return None
            
            # Connection reuse: check spreadsheet cache
            sheets_cache = env.setdefault('_gspread_sheets', {})
            if sheet_name in sheets_cache:
                sheet = sheets_cache[sheet_name]
            else:
                sheet = account.open(sheet_name)
                sheets_cache[sheet_name] = sheet
            
            # Singleton logging: only print connection info once per spreadsheet ID in THIS process
            global _PRINTED_CONNECTIONS
            if sheet.id not in _PRINTED_CONNECTIONS:
                _PRINTED_CONNECTIONS.add(sheet.id)
                connections[sheet.id] = {"title": sheet.title, "url": sheet.url}
                print(colourise("cyan", "[INFO]"), f"Connected to Spreadsheet: '{sheet.title}'")
                print(colourise("cyan", "[INFO]"), f"URL: {sheet.url}")
                
        except gspread.exceptions.SpreadsheetNotFound:
            print(colourise("yellow", "[WARN]"), \
                f"The spreadsheet '{sheet_name}' was not found.")
            
            try:
                print(colourise("cyan", "[INFO]"), f"Creating new spreadsheet: '{sheet_name}'...")
                sheet = account.create(sheet_name)
                sheets_cache[sheet_name] = sheet
                just_created = True
                print(colourise("green", "[SUCCESS]"), f"Created spreadsheet: '{sheet.title}'")
                print(colourise("green", "[INFO]"), f"URL: {sheet.url}")
                
                # Cache connection info for summary
                connections[sheet.id] = {"title": sheet.title, "url": sheet.url}
                
            except Exception as e:
                print(colourise("red", "[ABORT]"), f"Failed to create spreadsheet: {e}")
                return None

        # Check permissions and share with user if needed
        user_email = env.get('USER_EMAIL')
        if user_email:
            cache_key = f"{sheet.id}:{user_email}"
            if cache_key not in shared:
                try:
                    # If just created, we MUST notify so the user gets the link.
                    # If it already existed, we share with notify=False to ensure access without spam.
                    print(colourise("cyan", "[INFO]"), f"Ensuring access for {user_email}...")
                    sheet.share(user_email, perm_type='user', role='writer', notify=just_created)
                    print(colourise("green", "[SUCCESS]"), f"Shared with {user_email} (notify={just_created}).")
                    shared.add(cache_key)
                except Exception as e:
                    # Don't abort if sharing fails (might be Prod sheet owned by someone else)
                    print(colourise("yellow", "[WARN]"), f"Could not share spreadsheet: {e}")
        
        # Save updated cache
        cache["connections"] = connections
        cache["shared"] = list(shared)
        _save_process_cache(cache)

        # Opening the sheet validates access. If it fails, common errors are handled.
        
        # Open the Worksheet
        try:
            if worksheet_env_var not in env:
                 print(colourise("red", "[ABORT]"), f"{worksheet_env_var} environment variable not set")
                 return None
                 
            worksheet_name = env[worksheet_env_var]
            
            # Connection reuse: check worksheet cache
            ws_cache = env.setdefault('_gspread_worksheets', {})
            ws_key = f"{sheet.id}:{worksheet_name}"
            if ws_key in ws_cache:
                return ws_cache[ws_key]
                
            worksheet = sheet.worksheet(worksheet_name)
            ws_cache[ws_key] = worksheet
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            print(colourise("yellow", "[WARN]"), \
                f"The worksheet '{worksheet_name}' was not found.")
            
            try:
                print(colourise("cyan", "[INFO]"), f"Creating new worksheet: '{worksheet_name}'...")
                # Create worksheet with sensible default dimensions (enough columns for reports)
                worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=20)
                env.setdefault('_gspread_worksheets', {})[f"{sheet.id}:{worksheet_name}"] = worksheet
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

def hint_ssl_error(e):
    """Detect SSL certificate verification failure and provide a helpful hint for macOS users."""
    err_msg = str(e)
    if "[SSL: CERTIFICATE_VERIFY_FAILED]" in err_msg:
        print(colourise("yellow", "\n[HINT] SSL Certificate Verification Failed!"))
        print(colourise("gray", "This is common on macOS. You can:"))
        print(colourise("gray", f" 1. Run with the {colourise('bold', '--insecure')} flag to bypass this check."))
        print(colourise("gray", " 2. Run 'Install Certificates.command' in your Python folder (usually in /Applications)."))
        print(colourise("gray", " 3. Set SSL_CHECK=False in your .env file.\n"))

def get_logged_connections():
    """Return list of uniquely connected spreadsheets for summary info."""
    cache = _load_process_cache()
    return list(cache.get("connections", {}).values())

def clear_connection_cache():
    """Remove the local connection cache file (call at end of run or beginning of new run)."""
    if os.path.exists(_CACHE_FILE):
        try: os.remove(_CACHE_FILE)
        except: pass

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

def sync_slas_sheet_from_report(ws_slas, ws_report):
    """Populate SLAs sheet with filtered data from a report sheet (CloudReport or HTCReport).
    
    Shows all columns/data from the report, but only rows for VOs that are in the SLAs sheet.
    
    Args:
        ws_slas: The SLAs reference worksheet (contains VO list in column A)
        ws_report: The report worksheet to filter from (CloudReport or HTCReport)
    """
    try:
        # Get list of SLA VO names from column A (starting row 2, skip header)
        sla_data = ws_slas.get_all_values()
        if not sla_data or len(sla_data) < 2:
            return
        
        sla_vo_names = {row[0] for row in sla_data[1:] if row and len(row) > 0}
        if not sla_vo_names:
            return
        
        # Get all data from report sheet
        report_data = ws_report.get_all_values()
        if not report_data:
            return
        
        # Filter report rows to only include SLA VOs
        headers = report_data[0]
        filtered_rows = [headers]
        for row in report_data[1:]:
            if row and len(row) > 0 and row[0] in sla_vo_names:
                filtered_rows.append(row)
        
        # Write filtered data back to SLAs sheet
        print(colourise("cyan", "[INFO]"), f"Syncing {len(filtered_rows)-1} SLA VOs from {ws_report.title}...")
        ws_slas.update('A1', filtered_rows, value_input_option='RAW')
        print(colourise("green", "[SUCCESS]"), f"SLAs sheet synced with {len(filtered_rows)-1} VOs")
        
    except Exception as e:
        print(colourise("yellow", "[WARN]"), f"Failed to sync SLAs from {ws_report.title}: {e}")


# ----------------------------------------------------------------------------
# Confluence SLA VO fetcher
# ----------------------------------------------------------------------------

_CONFLUENCE_CUSTOMER_DB_PAGE_ID = "1867983"  # "Customer database" page, IMS space
_VO_PLACEHOLDERS = {"n/a", "see the table", "as in the sla agreement", "see above", "", "-"}


def _normalize_confluence_vo_name(raw):
    """Normalize a VO name value from Confluence, handling URL format.

    Examples:
      'vo.pangeo.eu'  -> 'vo.pangeo.eu'
      'https://operations-portal.egi.eu/vo/view/voname/youreact.vo.egi.eu' -> 'youreact.vo.egi.eu'
    """
    if not raw:
        return None
    raw = raw.strip()
    # Extract VO name from Operations Portal URL
    if "operations-portal.egi.eu" in raw and "voname/" in raw:
        raw = raw.split("voname/")[-1].rstrip("/")
    # Filter out placeholder text
    if raw.lower() in _VO_PLACEHOLDERS:
        return None
    # Filter out remaining URLs or multi-word sentences
    if raw.startswith("http") or " " in raw or len(raw) > 100:
        return None
    return raw


def _parse_confluence_customer_page(html_body):
    """Extract (vo_name, sla_status) from a Confluence customer page body (Storage Format)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(colourise("yellow", "[WARN]"), "BeautifulSoup (bs4) not installed. Confluence SLA parsing skipped.")
        return None, None

    soup = BeautifulSoup(html_body, "html.parser")
    vo_name = None
    sla_status = None

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        key = cells[0].get_text(strip=True)
        val = cells[1].get_text(strip=True)
        if key == "Virtual Organization":
            vo_name = _normalize_confluence_vo_name(val)
        elif key == "SLA status":
            sla_status = val.strip().upper()

    return vo_name, sla_status


def get_confluence_sla_vos(env):
    """Fetch VOs with FINALIZED SLA status from the Confluence IMS Customer database.

    Requires CONFLUENCE_SERVER_URL and CONFLUENCE_AUTH_TOKEN in env.
    Returns a sorted list of VO names, or [] if not configured / on error.
    """
    import concurrent.futures

    server_url = env.get("CONFLUENCE_SERVER_URL", "").rstrip("/") + "/"
    token = env.get("CONFLUENCE_AUTH_TOKEN", "")

    if not server_url or not token or token == "your_token_here":
        return []

    headers = {
        "Accept": "application/json",
        "user-agent": "egi-automation",
        "Authorization": f"Bearer {token}",
    }
    verify_ssl = env.get("SSL_CHECK", "True") != "False"

    # 1. Fetch all customer pages via CQL
    pages = []
    start = 0
    limit = 50
    try:
        while True:
            resp = requests.get(
                f"{server_url}rest/api/content/search",
                headers=headers,
                params={
                    "cql": f'label = "customer" and space = "IMS" and ancestor = {_CONFLUENCE_CUSTOMER_DB_PAGE_ID}',
                    "limit": limit,
                    "start": start,
                },
                verify=verify_ssl,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            pages.extend(results)
            if len(results) < limit:
                break
            start += limit
    except Exception as e:
        print(colourise("yellow", "[WARN]"), f"Confluence: failed to list customer pages: {e}")
        return []

    print(colourise("cyan", "[INFO]"), f"Confluence: processing {len(pages)} customer pages...")

    # 2. Fetch each page body in parallel (max 5 workers to avoid 429 rate-limiting)
    def _fetch_and_parse(page):
        page_id = page["id"]
        try:
            resp = requests.get(
                f"{server_url}rest/api/content/{page_id}",
                headers=headers,
                params={"expand": "body.storage"},
                verify=verify_ssl,
                timeout=15,
            )
            resp.raise_for_status()
            html = resp.json().get("body", {}).get("storage", {}).get("value", "")
            return _parse_confluence_customer_page(html)
        except Exception as e:
            if env.get("LOG") == "DEBUG":
                print(colourise("yellow", "[WARN]"), f"Confluence: failed page {page_id}: {e}")
            return None, None

    finalized_vos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for vo_name, sla_status in executor.map(_fetch_and_parse, pages):
            if vo_name and sla_status and "FINALIZED" in sla_status:
                finalized_vos.append(vo_name)

    finalized_vos = sorted(set(finalized_vos))
    print(colourise("green", "[SUCCESS]"), f"Confluence: found {len(finalized_vos)} FINALIZED SLA VOs")
    return finalized_vos
