
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
import concurrent.futures
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
        """Fetch accounting for a single VO using the custom selector (ensures coverage)."""
        parts_from = self.env['DATE_FROM'].replace("-", "/").split("/")
        parts_to = self.env['DATE_TO'].replace("-", "/").split("/")
        from_yr, from_mo = parts_from[0], parts_from[1].lstrip('0')
        to_yr, to_mo = parts_to[0], parts_to[1].lstrip('0')
        
        benchmark = self.env.get('ACCOUNTING_BENCHMARK_SELECTOR', 'hepspec06')
        url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/"
            f"{self.env['ACCOUNTING_SCOPE']}/"
            f"{self.env['ACCOUNTING_METRIC']}/"
            f"VO/DATE/{from_yr}/{from_mo}/{to_yr}/{to_mo}/"
            f"custom-{vo_name}/"
            f"{self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}/"
            f"{benchmark}/"
            f"{self.env['ACCOUNTING_DATA_SELECTOR']}/"
        )
        
        verify_ssl = self.env.get('SSL_CHECK', 'True') != 'False'
        try:
            # Use shared session for Keep-Alive and connection pooling
            r = self.session.get(url, verify=verify_ssl, timeout=30)
            r.raise_for_status()
            data = r.json()
            # For a single VO, find the 'Total' record or return 0
            for record in data:
                if "Total" in record.get('id', ''):
                    _raw = record.get('Total', 0)
                    try: return int(float(_raw)) if _raw else 0
                    except: return 0
            return 0
        except Exception as e:
            return 0

    def run(self, dry_run=False):
        scope = self.env.get('ACCOUNTING_SCOPE', '')
        print(f"\n[*] Module: SLA-{scope.upper()}")
        
        ws_key = 'GOOGLE_SLAs_CLOUD_WORKSHEET' if 'cloud' in scope else 'GOOGLE_SLAs_HTC_WORKSHEET'
        worksheet = self.init_worksheet(ws_key)
        
        vos = self.fetch_active_slas()
        print(colourise("cyan", f"\tFetching accounting for {len(vos)} active SLAs in parallel..."))
        
        cells_to_update = []
        total_cpu = 0
        
        # 1. Fetch data in parallel (High performance)
        vo_data = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            # Create mapping of Future -> VO name
            future_to_vo = {executor.submit(self.fetch_vo_accounting, vo['Name']): vo['Name'] for vo in vos}
            for future in concurrent.futures.as_completed(future_to_vo):
                vo_name = future_to_vo[future]
                try:
                    cpu = future.result()
                    total_cpu += cpu
                    vo_data.append((vo_name, cpu))
                except Exception as e:
                    vo_data.append((vo_name, 0))

        if dry_run:
            status = "(No Worksheet)" if not worksheet else ""
            print(f"\tSummary: {total_cpu} CPU/h across {len(vos)} SLAs {status}")
            return
            
        if not worksheet:
            print(colourise("red", "[ABORT]"), f"Worksheet {ws_key} not found.")
            return

        # 2. Setup Sheet (Single Read)
        all_rows = worksheet.get_all_values()
        headers = all_rows[0] if all_rows else []
        existing_names = [r[0] if r else "" for r in all_rows]
        
        # Ensure A1 has sensible header
        if not headers or not headers[0]:
            print(f"\tInitializing worksheet header...")
            worksheet.update('A1', [['VO']], value_input_option='RAW')
            headers = ['VO']

        # Apply uniform formatting
        self.apply_standard_formatting(worksheet)
        
        period_col = self.get_period_column(worksheet, headers=headers)

        # 3. Update Rows
        remaining_vos = []
        for name, cpu in vo_data:
            if name in existing_names:
                row_idx = existing_names.index(name) + 1
                cells_to_update.append(gspread.Cell(row_idx, period_col, cpu))
            else:
                remaining_vos.append((name, cpu))

        if remaining_vos:
            # Batch insert new ones
            remaining_vos.sort(key=lambda x: x[0])
            start_row = self.get_item_row(worksheet, remaining_vos[0][0], start_row=2, all_values=all_rows)
            
            print(f"\tInserting {len(remaining_vos)} new SLA entries at row {start_row}...")
            worksheet.insert_rows([[v[0]] for v in remaining_vos], row=start_row)
            
            for i, (name, cpu) in enumerate(remaining_vos):
                row = start_row + i
                cells_to_update.append(gspread.Cell(row, period_col, cpu))

        if cells_to_update:
            print(f"\tUpdating {len(cells_to_update)} SLA records...")
            worksheet.update_cells(cells_to_update, value_input_option='RAW')
            self.update_timestamp(worksheet)

if __name__ == "__main__":
    SLAsAccounting().run()
