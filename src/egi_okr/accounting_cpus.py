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

        _url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/custom_cloud.php?"
            f"query={self.env['ACCOUNTING_METRIC']}&option=REGION&"
            f"sYear={self.env['DATE_FROM'][:4]}&sMonth={self.env['DATE_FROM'][-2:]}&"
            f"eYear={self.env['DATE_TO'][:4]}&eMonth={self.env['DATE_TO'][-2:]}&"
            f"yrange=VO&xrange=DATE&localJobs={self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}&"
            f"groupVO={self.env['ACCOUNTING_VO_GROUP_SELECTOR']}&tree=cloud&optval=&json=API"
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
            
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            VOs_string = ', '.join([str(elem.get('VO name')) for elem in summary["VOs_complete_list"]]) if summary["VOs_complete_list"] else '-'
            NOVOs_string = ', '.join([str(item) for item in summary["noVOsCPUs"]]) if summary["noVOsCPUs"] else '-'

            # Idempotent logic: find existing period column A
            periods = worksheet.col_values(1)
            period_row = None
            if accounting_period in periods:
                period_row = periods.index(accounting_period) + 1
            
            if period_row:
                cell = worksheet.cell(period_row, 1)
                self.update_worksheet_cells(worksheet, cell, summary, VOs_string, NOVOs_string)
                logging.info(f"Updated the Total {'Cloud' if 'cloud' in scope else 'HTC'} CPU/h for the reporting period: {accounting_period} (row {period_row})")
            if not period_row:
                pos, _ = self.get_cell_position(worksheet, accounting_period)
                logging.info(f"Adding {accounting_period} at row: {pos}")
                
                result = '-'
                if pos > 2:
                    # Get previous period VOs from column D (4)
                    prev_vos = worksheet.cell(pos - 1, 4).value
                # Columns: Period, CPU/h, Total VOs, VOs List, No CPU Count, No CPU List, Diff
                body = [
                    accounting_period,
                    summary["total_cloud_cpu_hours"] if 'cloud' in scope else summary["total_htc_cpu"],
                    summary["total"],
                    VOs_string,
                    len(summary["noVOsCPUs"]),
                    NOVOs_string,
                    result
                ]
                worksheet.insert_row(body, index=pos, inherit_from_before=True)

            worksheet.insert_note("A1", f"Last update on: {timestamp}")

        except (GSpreadException, ValueError) as e:
            handle_exception(e, self.env, worksheet)

    def update_worksheet_cells(self, worksheet, cell, summary, VOs_string, NOVOs_string):
        scope = self.env.get('ACCOUNTING_SCOPE', '')
        cpu_val = summary["total_cloud_cpu_hours"] if 'cloud' in scope else summary["total_htc_cpu"]
        
        # Update worksheet cells
        worksheet.update_cell(cell.row, cell.col + 1, cpu_val)
        worksheet.update_cell(cell.row, cell.col + 2, summary["total"])
        worksheet.update_cell(cell.row, cell.col + 3, VOs_string)
        worksheet.update_cell(cell.row, cell.col + 4, len(summary["noVOsCPUs"]))
        worksheet.update_cell(cell.row, cell.col + 5, NOVOs_string)
        
        if cell.row > 2:
             # Recalculate diff
             prev_vos = worksheet.cell(cell.row - 1, 4).value
             # current is VOs_string
             newVOs_str, leavingVOs_str = find_difference(prev_vos, VOs_string)
             result = f"APPEARED: {newVOs_str}\nDISAPPEARED: {leavingVOs_str}"
             worksheet.update_cell(cell.row, cell.col + 6, result)
        else:
             worksheet.update_cell(cell.row, cell.col + 6, '-')


    def get_cell_position(self, worksheet, accounting_period):
        pos = 2
        found = False
        values_list = worksheet.col_values(1)
        if len(values_list) > 1:
            for header in values_list:
                if "Period" not in header:
                    if header == accounting_period or header == "":
                        found = True
                        break
                    if header < accounting_period:
                        pos += 1
        return pos, found

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
