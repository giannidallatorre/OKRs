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

import gspread
import json
import warnings
from utils import colourise

warnings.filterwarnings("ignore")

__author__    = "Giuseppe LA ROCCA"
__email__     = "giuseppe.larocca@egi.eu"
__version__   = "$Revision: 0.2"
__date__      = "$Date: 25/04/2024 11:58:27"
__copyright__ = "Copyright (c) 2024 EGI Foundation"
__license__   = "Apache Licence v2.0"

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
           not service_info['private_key'].endswith('-----END PRIVATE KEY-----\n'):
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

def init_GWorkSheet(env):
    """Initialize the GWorkSheet settings and return the worksheet"""
    try:
        # Get the service account
        account = init_google_credentials(env)
        if not account:
            return None

        # Validate spreadsheet access
        if not validate_spreadsheet_access(account, env):
            return None

        # Open the GoogleSheet
        try:
            sheet = account.open(env['GOOGLE_SHEET_NAME'])
        except gspread.exceptions.SpreadsheetNotFound:
            print(colourise("red", "[ABORT]"), \
                "The GOOGLE_SHEET_NAME setting points to a non-existent sheet")
            return None

        # Open the Worksheet
        try:
            worksheet = sheet.worksheet(env['GOOGLE_SERVICE_ORDERS_WORKSHEET'])
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            print(colourise("red", "[ABORT]"), \
                "The GOOGLE_SERVICE_ORDERS_WORKSHEET setting points to a non-existent worksheet")
            return None

    except KeyError as e:
        print(colourise("red", "[ABORT]"), \
            f"Missing required environment variable: {e}")
        return None
    except Exception as e:
        print(colourise("red", "[ABORT]"), \
            f"Unexpected error: {e}")
        return None

