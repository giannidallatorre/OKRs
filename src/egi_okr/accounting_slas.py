
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
import json
import gspread
from .base_accounting import BaseAccounting
from .utils import handle_exception, colourise

class SLAsAccounting(BaseAccounting):
    def __init__(self, env=None):
        super().__init__(env)

    def fetch_active_slas(self):
        """Fetch active SLAs from Spreadsheet OR API fallback."""
        vos = []
        try:
             mock_env = self.env.copy()
             mock_env['GOOGLE_SHEET_NAME'] = self.env.get('GOOGLE_SLAs_SHEET_NAME', self.env.get('GOOGLE_SHEET_NAME'))
             sla_ws = self.init_worksheet('GOOGLE_SLAs_WORKSHEET')
             if sla_ws:
                 values = sla_ws.get_all_values()
                 for value in values[1:]:
                     if len(value) > 16 and value[6] == "FINALIZED":
                         vo_name = value[10]
                         sla_type = "cloud" if value[16].upper() == "TRUE" else "htc"
                         if sla_type in self.env.get('ACCOUNTING_SCOPE', ''):
                             vos.append({"Customer": value[0], "Name": vo_name, "CPU/h": 0, "Type": sla_type})
        except Exception as e:
             print(colourise("yellow", "[WARN]"), f"Failed to read SLA sheet: {e}")

        if not vos:
            print(colourise("yellow", "[INFO]"), "Fetching VOs from API as SLA fallback...")
            from .operations import get_VOs_stats
            vos = [{"Name": v['name'], "CPU/h": 0} for v in get_VOs_stats(self.env)]
        return vos

    def fetch_vo_accounting(self, vo_name):
        parts_from = self.env['DATE_FROM'].replace("-", "/").split("/")
        parts_to = self.env['DATE_TO'].replace("-", "/").split("/")
        from_yr, from_mo = parts_from[0], parts_from[1].lstrip('0')
        to_yr, to_mo = parts_to[0], parts_to[1].lstrip('0')
        
        benchmark = self.env.get('ACCOUNTING_BENCHMARK_SELECTOR', 'hepspec06')
        url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/"
            f"{self.env['ACCOUNTING_SCOPE']}/"
            f"{self.env['ACCOUNTING_METRIC']}/"
            f"REGION/Year/{from_yr}/{from_mo}/{to_yr}/{to_mo}/"
            f"custom-{vo_name}/"
            f"{self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}/"
            f"{benchmark}/"
            f"{self.env['ACCOUNTING_DATA_SELECTOR']}/"
        )
        
        verify_ssl = self.env.get('SSL_CHECK', 'True') != 'False'
        try:
            r = requests.get(url, verify=verify_ssl)
            r.raise_for_status()
            data = r.json()
            return sum([int(rec.get('Total', 0)) for rec in data if 'Total' in rec])
        except: return 0

    def run(self, dry_run=False):
        scope = self.env.get('ACCOUNTING_SCOPE', '')
        print(f"\n[*] Module: SLA-{scope.upper()}")
        
        ws_key = 'GOOGLE_SLAs_CLOUD_WORKSHEET' if 'cloud' in scope else 'GOOGLE_SLAs_HTC_WORKSHEET'
        worksheet = self.init_worksheet(ws_key)
        
        vos = self.fetch_active_slas()
        print(f"\tProcessing {len(vos)} active SLAs...")
        
        cells_to_update = []
        total_cpu = 0
        
        # 1. Fetch data for all (dry-run ready)
        vo_data = []
        for vo in vos:
            cpu = self.fetch_vo_accounting(vo['Name'])
            total_cpu += cpu
            vo_data.append((vo['Name'], cpu))

        if dry_run:
            status = "(No Worksheet)" if not worksheet else ""
            print(f"\tSummary: {total_cpu} CPU/h across {len(vos)} SLAs {status}")
            return
            
        if not worksheet:
            print(colourise("red", "[ABORT]"), f"Worksheet {ws_key} not found.")
            return

        # 2. Setup Sheet
        period_col = self.get_period_column(worksheet)
        self.apply_standard_formatting(worksheet)

        # 3. Update Rows
        for name, cpu in vo_data:
            row_idx = self.get_item_row(worksheet, name, start_row=2)
            current_val = worksheet.cell(row_idx, 1).value
            if current_val != name:
                worksheet.insert_row([name], index=row_idx)
            cells_to_update.append(gspread.Cell(row_idx, period_col, cpu))

        if cells_to_update:
            print(f"\tUpdating {len(cells_to_update)} SLA records...")
            worksheet.update_cells(cells_to_update, value_input_option='RAW')
            self.update_timestamp(worksheet)

if __name__ == "__main__":
    SLAsAccounting().run()
