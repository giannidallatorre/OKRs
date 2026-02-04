
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
import gspread
from .base_accounting import BaseAccounting
from .utils import handle_exception, find_difference, colourise

class CPUAccounting(BaseAccounting):
    def __init__(self, env=None):
        super().__init__(env)

    def fetch_accounting_data(self):
        """Fetch accounting data from the EGI Accounting Portal."""
        parts_from = self.env['DATE_FROM'].replace("-", "/").split("/")
        parts_to = self.env['DATE_TO'].replace("-", "/").split("/")
        from_year, from_month = parts_from[0], parts_from[1].lstrip('0')
        to_year, to_month = parts_to[0], parts_to[1].lstrip('0')
        
        _url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/"
            f"{self.env['ACCOUNTING_SCOPE']}/"
            f"{self.env['ACCOUNTING_METRIC']}/"
            f"VO/DATE/{from_year}/{from_month}/{to_year}/{to_month}/"
            f"{self.env['ACCOUNTING_VO_GROUP_SELECTOR']}/"
            f"{self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}/"
            f"{self.env.get('ACCOUNTING_BENCHMARK_SELECTOR', 'hepspec06')}/"
            f"{self.env['ACCOUNTING_DATA_SELECTOR']}/"
        )
        
        verify_ssl = self.env.get('SSL_CHECK', 'True') != 'False'
        try:
            response = requests.get(url=_url, headers={"Accept": "application/json"}, verify=verify_ssl)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"[ERROR] Failed to fetch accounting data: {e}")
            return []

    def process_accounting_data(self, data):
        summary = {"total": 0, "total_cpu": 0, "noVOs": [], "VOs": []}
        scope = self.env.get('ACCOUNTING_SCOPE', '')

        for record in data:
            total_val = record.get('Total', 0)
            if "Total" in record['id']:
                summary["total_cpu"] = total_val
                continue

            if "Percent" in record['id'] or 'Total' not in record:
                continue

            if total_val > 0:
                summary["VOs"].append(record['id'])
                summary["total"] += 1
            elif scope == "cloud":
                summary["noVOs"].append(record['id'])

        return summary

    def run(self, dry_run=False):
        scope = self.env.get('ACCOUNTING_SCOPE', '')
        print(f"\n[*] Module: CPU-{scope.upper()}")
        
        worksheet_key = 'GOOGLE_CLOUD_WORKSHEET' if 'cloud' in scope else 'GOOGLE_HTC_WORKSHEET'
        worksheet = self.init_worksheet(worksheet_key)
        
        data = self.fetch_accounting_data()
        summary = self.process_accounting_data(data)

        if dry_run:
            status = "(No Worksheet)" if not worksheet else ""
            print(f"\tSummary: {summary['total_cpu']} CPU/h across {summary['total']} VOs {status}")
            return
            
        if not worksheet:
            print(colourise("red", "[ABORT]"), f"Worksheet {worksheet_key} not found.")
            return

        # 1. Setup & Orientation
        headers = worksheet.row_values(1)
        all_values = worksheet.get_all_values()
        
        labels = ["Period Metric", "CPU/h", "#VOs with accounting", "List of active VOs", "#VOs without accounting", "VOs with *NO* accounting", "VOs variations", "Follow-up actions"]
        if not headers or labels[0] not in headers[0]:
            print(f"\tInitializing worksheet labels...")
            worksheet.update('A1', [[l] for l in labels], value_input_option='RAW')
            headers = [labels[0]] # Refresh headers for get_period_column
        
        period_col = self.get_period_column(worksheet, headers=headers)
        self.apply_standard_formatting(worksheet)

        # 2. Diff Logic (Reuse all_values)
        result = '-'
        if period_col > 2 and len(all_values) >= 4:
            try:
                # Row 4 (index 3) is "List of active VOs"
                prev_vos = all_values[3][period_col - 2] if len(all_values[3]) >= (period_col - 1) else ""
                new_vo, left_vo = find_difference(prev_vos, ', '.join(summary["VOs"]))
                result = f"APPEARED: {new_vo}\nDISAPPEARED: {left_vo}"
            except: pass

        # 3. Write
        col_values = [[summary["total_cpu"]], [summary["total"]], [', '.join(summary["VOs"]) or '-'], [len(summary["noVOs"])], [', '.join(summary["noVOs"]) or '-'], [result], ['-']]
        col_letter = gspread.utils.rowcol_to_a1(1, period_col)[:-1]
        
        print(f"\tWriting data to column {col_letter}...")
        worksheet.update(f"{col_letter}2:{col_letter}8", col_values, value_input_option='RAW')
        self.update_timestamp(worksheet)

if __name__ == "__main__":
    CPUAccounting().run()
