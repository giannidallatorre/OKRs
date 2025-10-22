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
import logging
import traceback
from dotenv import load_dotenv

def find_difference(activeVOs_1, activeVOs_2):
    ''' Find difference between two comma-separated strings '''

    set_1 = set(activeVOs_1.split(", ")) if activeVOs_1 else set()
    set_2 = set(activeVOs_2.split(", ")) if activeVOs_2 else set()

    arrivingVOs = set_2 - set_1
    leavingVOs = set_1 - set_2

    arrivingVOs_str = ', '.join(arrivingVOs) if arrivingVOs else "-"
    leavingVOs_str = ', '.join(leavingVOs) if leavingVOs else "-"

    return arrivingVOs_str, leavingVOs_str

def colourise(colour, text):
    ''' Colourise - colours text in shell. Returns plain if colour doesn't exist '''

    colours = {
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "gray": "37"
    }

    colour_code = colours.get(colour)
    return f"\033[1;{colour_code}m{text}\033[1;m" if colour_code else text

def highlight(colour, text):
    ''' Highlight - highlights text in shell. Returns plain if colour doesn't exist. '''

    colours = {
        "black": "40",
        "red": "41",
        "green": "42",
        "yellow": "43",
        "blue": "44",
        "magenta": "45",
        "gray": "47"
    }

    return f"\033[1;{colours.get(colour, '')}m{text}\033[1;m" if colour in colours else text

def get_env_settings():
    ''' Reading profile settings from env '''

    # Load environment variables from .env files in the .config folder
    config_path = os.path.join(os.path.dirname(__file__), '../../../.config')
    print(f"Loading .env files from directory: {config_path}")

    load_dotenv(os.path.join(config_path, '.env'))
    load_dotenv(os.path.join(config_path, '.env.egi'))
    load_dotenv(os.path.join(config_path, '.env.google'))

    env_vars = [
        'ACCOUNTING_SERVER_URL', 'ACCOUNTING_SCOPE', 'ACCOUNTING_METRIC',
        'ACCOUNTING_LOCAL_JOB_SELECTOR', 'ACCOUNTING_VO_GROUP_SELECTOR', 'ACCOUNTING_DATA_SELECTOR',
        'SERVICE_ACCOUNT_FILE', 'GOOGLE_SHEET_NAME',
        'GOOGLE_CLOUD_WORKSHEET', 'GOOGLE_HTC_WORKSHEET', 'LOG', 'DATE_FROM', 'DATE_TO', 'SSL_CHECK'
    ]

    d = {}
    missing_vars = []

    for var in env_vars:
        try:
            d[var] = os.environ[var]
        except KeyError:
            missing_vars.append(var)

    if missing_vars:
        missing_vars_str = ', '.join(missing_vars)
        logging.error(f"ERROR: Environment variables {missing_vars_str} not found!")
        raise KeyError(f"Missing environment variables: {missing_vars_str}")

    return d

def handle_exception(e, env, worksheet=None):
    ''' Handle exceptions and print detailed error messages '''
    logging.error(f"ERROR: {e}")
    if worksheet:
        logging.error(f"Spreadsheet: {worksheet.spreadsheet.title}")
        logging.error(f"Worksheet: {worksheet.title}")
    logging.error("Please ensure that the header row in the worksheet is unique.")
    logging.error("Check for duplicate column headers and make sure each header is unique.")
    
    if logging.getLogger().level == logging.DEBUG:
        logging.debug("\n[DEBUG] Traceback:")
        logging.debug(traceback.format_exc())