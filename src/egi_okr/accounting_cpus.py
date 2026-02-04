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

import requests
import logging
import datetime
import json
import os
from gspread.exceptions import GSpreadException
from .utils import get_env_settings, handle_exception, init_GWorkSheet, find_difference, format_reporting_period

class CPUAccounting:
    def __init__(self, env=None):
        self.env = env if env is not None else get_env_settings()

    def fetch_accounting_data(self):
        ''' Fetch accounting data from the EGI Accounting Portal '''
        if not self.env.get('ACCOUNTING_SERVER_URL'):
            raise ValueError("ACCOUNTING_SERVER_URL not set")

        # EGI Accounting Portal has migrated to a new Django-based system.
        # The legacy custom_cloud.php endpoint is deprecated and returns 404.
        # We use the REST-like URL structure which redirects to the correct portal service.
        # Pattern: {SERVER}/{SCOPE}/{METRIC}/VO/DATE/{DATE_FROM}/{DATE_TO}/{VO_GROUP}/{LOCAL_JOBS}/{DATA_SELECTOR}/
        
        # Ensure dates are in YYYY/M format (no leading zeros for months as required by the new portal)
        parts_from = self.env['DATE_FROM'].replace("-", "/").split("/")
        parts_to = self.env['DATE_TO'].replace("-", "/").split("/")
        
        # Strip leading zeros
        from_year, from_month = parts_from[0], parts_from[1].lstrip('0')
        to_year, to_month = parts_to[0], parts_to[1].lstrip('0')
        
        _url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/"
            f"{self.env['ACCOUNTING_SCOPE']}/"
            f"{self.env['ACCOUNTING_METRIC']}/"
            f"VO/DATE/{from_year}/{from_month}/{to_year}/{to_month}/"
            f"{self.env['ACCOUNTING_VO_GROUP_SELECTOR']}/"
            f"{self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}/"
            f"{self.env['ACCOUNTING_BENCHMARK_SELECTOR']}/"
            f"{self.env['ACCOUNTING_DATA_SELECTOR']}/"
        )

        headers = {"Accept": "application/json"}
        logging.debug(f"Fetching accounting records from: {_url}")

        verify_ssl = self.env.get('SSL_CHECK', 'True') != 'False'
        try:
            response = requests.get(url=_url, headers=headers, verify=verify_ssl)
            response.raise_for_status()
            data = response.json()
            logging.debug(f"Response content: {data}")
            return data
        except Exception as e:
            logging.error(f"[ERROR] - Failed to fetch accounting data: {e}")
            return []

    def is_valid_record(self, record):
        ''' Check if the record is valid '''
        return "Percent" not in record['id'] and "Total" not in record['id'] and 'Total' in record

    def process_accounting_data(self, data):
        ''' Process the fetched accounting data '''
        logging.debug("Starting to process accounting data")

        summary = {
            "total": 0,
            "total_noVOsCPUs": 0,
            "total_cloud_cpu_hours": 0,
            "total_htc_cpu": 0,
            "noVOsCPUs": [],
            "VOs_complete_list": []
        }

        scope = self.env.get('ACCOUNTING_SCOPE', '')

        for record in data:
            total_cpu_hours = record.get('Total', 0)
            if "Total" in record['id']:
                if "cloud" in scope:
                    summary["total_cloud_cpu_hours"] = total_cpu_hours
                else:
                    summary["total_htc_cpu"] = total_cpu_hours
                continue

            if not self.is_valid_record(record):
                continue

            total_cpu_hours = record['Total']
            if total_cpu_hours > 0:
                summary["VOs_complete_list"].append({
                    "VO name": record['id'],
                    "CPU/h": f"{total_cpu_hours:7,d}"
                })
                summary["total"] += 1
            elif scope == "cloud":
                summary["total_noVOsCPUs"] += 1
                summary["noVOsCPUs"].append(record['id'])

        logging.debug(f"Processing summary: {summary}")
        return summary

    def format_worksheet(self, worksheet):
        worksheet.format("A1:H1", {
            "backgroundColor": {"red": 55.0, "green": 15.0, "blue": 10.0},
            "horizontalAlignment": "LEFT",
            "textFormat": {"fontSize": 11, "bold": True}
        })
        worksheet.format("A2:H100", {
            "horizontalAlignment": "RIGHT",
            "textFormat": {"fontSize": 11}
        })

    def update_headers(self, worksheet, accounting_period):
        """Ensure Metric labels in Column A and find/add Period in Row 1."""
        scope = self.env.get('ACCOUNTING_SCOPE', '')
        cpu_header = "Cloud CPU/h" if 'cloud' in scope else "HTC CPU/h"
        
        # Consistent label set for Column A
        labels = [
            "Period Metric", # A1
            cpu_header, 
            "#VOs with accounting", 
            "List of active VOs", 
            "#VOs without accounting", 
            "VOs with *NO* accounting", 
            "VOs variations (since the previous period)", 
            "Follow-up actions (with VOs with no accounting)"
        ]
        
        # 1. Ensure Column A has the labels
        first_col = worksheet.col_values(1)
        if not first_col or first_col[0] != "Period Metric":
             print(f"\tInitializing Metric labels in Column A...")
             # Prepare vertical data
             col_data = [[l] for l in labels]
             worksheet.update('A1', col_data, value_input_option='RAW')
        
        # 2. Ensure period exists in Row 1
        period_col, found = self.get_period_col_position(worksheet, accounting_period)
        
        if not found:
            print(f"\tAdding '{accounting_period}' at column: {period_col}")
            # Insert column for period
            # We insert empty values or maybe just header
            worksheet.insert_cols([[accounting_period]], period_col, value_input_option='RAW', inherit_from_before=True)
            
        return period_col

    def get_period_col_position(self, worksheet, accounting_period):
        """Find the column position for the reporting period in Row 1."""
        pos = 2
        found = False
        headers = worksheet.row_values(1)
        if len(headers) > 0:
            for i, h in enumerate(headers):
                if i == 0: continue # Skip 'Period Metric'
                if h == accounting_period:
                    pos = i + 1
                    found = True
                    break
                if h == "" or h == "TOTAL":
                    break
                if h < accounting_period:
                    pos = i + 2
                else:
                    pos = i + 1
                    break
        return pos, found

    def update_worksheet(self, summary):
        scope = self.env.get('ACCOUNTING_SCOPE', '')
        # Determine correct worksheet key
        if 'cloud' in scope:
            worksheet_key = 'GOOGLE_CLOUD_WORKSHEET'
        else:
            worksheet_key = 'GOOGLE_HTC_WORKSHEET'
        
        worksheet = init_GWorkSheet(self.env, worksheet_key)
        if not worksheet:
            return

        accounting_period = format_reporting_period(self.env)
        
        try:
            self.format_worksheet(worksheet)
            
            # Ensure orientation and get period column
            period_col = self.update_headers(worksheet, accounting_period)
            
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            VOs_string = ', '.join([str(elem.get('VO name')) for elem in summary["VOs_complete_list"]]) if summary["VOs_complete_list"] else '-'
            NOVOs_string = ', '.join([str(item) for item in summary["noVOsCPUs"]]) if summary["noVOsCPUs"] else '-'

            # Calculate difference since previous period
            # Previous period is the column to the left (period_col - 1)
            result = '-'
            if period_col > 2:
                 try:
                     # Get previous period VOs from row 4 (List of active VOs), previous col
                     prev_vos = worksheet.cell(4, period_col - 1).value
                     newVOs_str, leavingVOs_str = find_difference(prev_vos, VOs_string)
                     result = f"APPEARED: {newVOs_str}\nDISAPPEARED: {leavingVOs_str}"
                 except:
                     pass

            # Update the column values for the period rows 2 to 8
            # Rows correspond to the labels list in update_headers
            cpu_val = summary["total_cloud_cpu_hours"] if 'cloud' in scope else summary["total_htc_cpu"]
            
            col_values = [
                # Row 2: CPU val
                cpu_val,
                # Row 3: Total counted
                summary["total"],
                # Row 4: VOs List
                VOs_string,
                # Row 5: No CPU count
                len(summary["noVOsCPUs"]),
                # Row 6: No CPU List
                NOVOs_string,
                # Row 7: Diff
                result,
                # Row 8: Follow up
                '-'
            ]
            
            # Convert to Cell update list for batch update_cells
            cells_to_update = []
            for i, val in enumerate(col_values):
                row_idx = i + 2 # Metrics start at Row 2
                cells_to_update.append(gspread.Cell(row_idx, period_col, val))
            
            print(f"[INFO] Updating {accounting_period} in column {period_col}...")
            worksheet.update_cells(cells_to_update, value_input_option='RAW')

            worksheet.insert_note("A1", f"Last update on: {timestamp}")

        except (GSpreadException, ValueError) as e:
            handle_exception(e, self.env, worksheet)

    def run(self, dry_run=False):
        log_level = "DEBUG" if self.env.get('LOG') == "DEBUG" else "INFO"
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
        
        accounting_period = format_reporting_period(self.env)
        logging.info(f"[INFO] Reporting Period: {accounting_period}")

        if accounting_period in ["UNKNOWN_PERIOD", "INVALID_PERIOD"]:
            logging.error("[ABORT] Cannot proceed with invalid or unknown reporting period.")
            return

        try:
            data = self.fetch_accounting_data()
            summary = self.process_accounting_data(data)
            
            if dry_run:
                print(f"Reporting Period: {accounting_period}")
                print(f"Total VOs with accounting records: {summary['total']}")
                print(f"Total VOs with no accounting records: {summary['total_noVOsCPUs']}")
                if 'cloud' in self.env.get('ACCOUNTING_SCOPE', ''):
                    print(f"Total Cloud CPU/h: {summary['total_cloud_cpu_hours']}")
                else:
                    print(f"Total HTC CPU/h: {summary['total_htc_cpu']}")
            else:
                self.update_worksheet(summary)

        except Exception as e:
            handle_exception(e, self.env)

if __name__ == "__main__":
    # Can be run directly
    import argparse
    parser = argparse.ArgumentParser(description="Run CPU Accounting")
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose logging")
    parser.add_argument('--dry-run', action='store_true', help="Dry run")
    args = parser.parse_args()
    
    # Set log level in env if verbose
    if args.verbose:
        os.environ['LOG'] = 'DEBUG'
        
    app = CPUAccounting()
    app.run(dry_run=args.dry_run)
