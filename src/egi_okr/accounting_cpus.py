
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
            response = self.session.get(url=_url, headers={"Accept": "application/json"}, verify=verify_ssl, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            from .utils import hint_ssl_error
            logging.error(f"[ERROR] Failed to fetch accounting data: {e}")
            hint_ssl_error(e)
            raise e

    def process_accounting_data(self, data):
        summary = {"total": 0, "total_cpu": 0, "noVOs": [], "VOs": []}
        scope = self.env.get('ACCOUNTING_SCOPE', '')

        for record in data:
            _raw = record.get('Total', 0)
            try:
                total_val = int(float(_raw)) if _raw else 0
            except:
                total_val = 0

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
        
        try:
            data = self.fetch_accounting_data()
            summary = self.process_accounting_data(data)
        except Exception:
            if dry_run or self.print_mode:
                 status = "(Print Mode)" if self.print_mode else "(Dry Run)"
                 print(colourise("red", f"\t{status}: ABORTED (Data fetch failed)"))
            return

        if dry_run or self.print_mode:
            status = "(Print Mode)" if self.print_mode else "(Dry Run)"
            print(colourise("green", f"\t{status}: {summary['total_cpu']} CPU/h across {summary['total']} VOs"))
            if self.print_mode:
                print(f"\tActive VOs: {', '.join(summary['VOs'])}")
                if summary['noVOs']:
                    print(f"\tVOs with NO accounting: {', '.join(summary['noVOs'])}")
            return
            
        if not worksheet:
            print(colourise("red", "[ABORT]"), f"Worksheet {worksheet_key} not found.")
            return

        # 1. Setup Data for Centralized Update
        labels = ["CPU/h", "#VOs with accounting", "List of active VOs", "#VOs without accounting", "VOs with *NO* accounting", "VOs variations", "Follow-up actions"]
        
        # 2. Diff Logic (Requires a quick look at existing data for variations)
        # We can pass a pre-read all_values if we want, but update_worksheet_data handles it internally.
        # To calculate variations, we need the previous period's VO list.
        all_values = worksheet.get_all_values()
        headers = all_values[0] if all_values else []
        period_col = self.get_period_column(worksheet, headers=headers)
        
        variations = '-'
        if period_col > 2 and len(all_values) >= 4:
            try:
                # Row 4 (index 3) is "List of active VOs"
                prev_vos = all_values[3][period_col - 2] if len(all_values[3]) >= (period_col - 1) else ""
                new_vo, left_vo = find_difference(prev_vos, ', '.join(summary["VOs"]))
                variations = f"APPEARED: {new_vo}\nDISAPPEARED: {left_vo}"
            except: pass

        data_map = {
            "CPU/h": summary["total_cpu"],
            "#VOs with accounting": summary["total"],
            "List of active VOs": ', '.join(summary["VOs"]) or '-',
            "#VOs without accounting": len(summary["noVOs"]),
            "VOs with *NO* accounting": ', '.join(summary["noVOs"]) or '-',
            "VOs variations": variations,
            "Follow-up actions": '-'
        }

        # 3. Centralized Update
        print(f"\tUpdating worksheet '{worksheet.title}'...")
        self.update_worksheet_data(
            worksheet, 
            row_labels=labels, 
            data_map=data_map, 
            first_col_label="Metric",
            period_col=period_col
        )

if __name__ == "__main__":
    CPUAccounting().run()
