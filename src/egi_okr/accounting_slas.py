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

import datetime
import json
import requests
import gspread
from .utils import get_env_settings, handle_exception, init_GWorkSheet, colourise, format_reporting_period
from .operations import get_VOs_stats

class SLAsAccounting:
    def __init__(self, env=None):
        self.env = env if env is not None else get_env_settings()

    def get_period_col_position(self, worksheet, accounting_period):
        """Find the column position for the reporting period in Row 1."""
        try:
            cell = worksheet.find(accounting_period)
            if cell and cell.row == 1:
                return cell.col, True
        except:
            pass
        
        # Determine position lexicographically among existing periods
        pos = 2
        headers = worksheet.row_values(1)
        if len(headers) > 0:
            for i, header in enumerate(headers):
                if i == 0: continue # Skip VO
                if header == "" or header == "TOTAL":
                    break
                if header < accounting_period:
                    pos = i + 2
                else:
                    pos = i + 1
                    break
        return pos, False

    def get_vo_row_position(self, worksheet, vo_name):
        """Find the row position for a VO in Column A."""
        try:
            cell = worksheet.find(vo_name)
            if cell and cell.col == 1:
                return cell.row, True
        except:
            pass

        pos = 2
        values_list = worksheet.col_values(1)
        if len(values_list) > 1:
             for i, header in enumerate(values_list):
                 if i == 0: continue # Skip 'VO' header
                 if header == "":
                     break
                 if header < vo_name:
                     pos = i + 2
                 else:
                     pos = i + 1
                     break
        
        return pos, False

    def ensure_vo_row(self, worksheet, vo_name):
        """Find or insert VO row."""
        vo_row, found = self.get_vo_row_position(worksheet, vo_name)
        
        if not found:
             print(colourise("green", "[INFO]"), f"Adding '{vo_name}' at row: {vo_row}")
             worksheet.insert_row([vo_name], vo_row, value_input_option='RAW', inherit_from_before=False)
        
        return vo_row

    def fetch_slas_from_api(self):
        """Fetch VOs from Operations Portal API as a fallback for SLA list."""
        print(colourise("yellow", "[INFO]"), "Fetching VOs from API to use as SLA list...")
        
        vos_stats = get_VOs_stats(self.env)
        slas = []
        
        for vo in vos_stats:
            slas.append({
                "Customer": vo['name'], 
                "Name": vo['name'],
                "CPU/h": 0,
                "SLA_start": self.env['DATE_FROM'],
                "SLA_end": self.env['DATE_TO'],
                "Active": "Y",
                "Type": "egi, cloud"
            })
            
        print(colourise("green", "[INFO]"), f"Loaded {len(slas)} VOs from API.")
        return slas

    def fetch_active_slas(self):
        slas_ws = init_GWorkSheet(self.env, 'GOOGLE_SLAs_WORKSHEET', 'GOOGLE_SLAs_SHEET_NAME')
        
        vos = []
        if slas_ws:
            print(colourise("green", "\n[INFO]"), "Fetching active SLAs from Spreadsheet...")
            try:
                values = slas_ws.get_all_values()
                for value in values:
                     if len(value) < 17 or "VO name" in value[10]:
                         continue
                     status = value[6]
                     vo_name = value[10]
                     if "FINALIZED" in status:
                         sla_type = ""
                         v12 = value[12]
                         v16 = value[16]
                         if vo_name and v12 and not v16: sla_type = "egi"
                         elif vo_name and not v12 and v16: sla_type = "cloud"
                         elif vo_name and v12 and v16: sla_type = "egi, cloud"
                         if sla_type:
                             vos.append({
                                 "Customer": value[0],
                                 "Name": vo_name,
                                 "CPU/h": 0,
                                 "SLA_start": value[7],
                                 "SLA_end": value[8],
                                 "Active": "Y",
                                 "Type": sla_type
                             })
            except Exception as e:
                print(colourise("yellow", "[WARN]"), f"Failed to read SLA sheet: {e}")

        if not vos:
            print(colourise("yellow", "[WARN]"), "No active SLAs found in spreadsheet (or tab missing).")
            vos = self.fetch_slas_from_api()
        return vos

    def fetch_vo_accounting(self, vo_name):
        date_from = self.env['DATE_FROM'].replace("-", "/")
        date_to = self.env['DATE_TO'].replace("-", "/")
        url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/"
            f"{self.env['ACCOUNTING_SCOPE']}/"
            f"{self.env['ACCOUNTING_METRIC']}/"
            f"REGION/Year/{date_from}/{date_to}/"
            f"custom-{vo_name}/"
            f"{self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}/"
            f"{self.env['ACCOUNTING_DATA_SELECTOR']}/"
        )
        verify_ssl = self.env.get('SSL_CHECK', 'True') != 'False'
        try:
             response = requests.get(url, verify=verify_ssl)
             response.raise_for_status()
             return response.json()
        except Exception as e:
             if self.env.get('LOG') == "DEBUG":
                  print(colourise("red", "[ERROR]"), f"Failed to fetch accounting for {vo_name}: {e}")
             return None

    def main(self, dry_run=False):
        log_level = self.env.get('LOG', 'INFO')
        print(f"\nLog Level = {colourise('cyan', log_level)}")
        
        reporting_period = format_reporting_period(self.env)
        print(colourise("cyan", "\n[INFO]"), f"Reporting Period: {reporting_period}")

        if reporting_period in ["UNKNOWN_PERIOD", "INVALID_PERIOD"]:
            print(colourise("red", "[ABORT]"), "Cannot proceed with invalid or unknown reporting period.")
            return

        scope = self.env.get('ACCOUNTING_SCOPE', '')
        if 'cloud' in scope:
            target_ws_key = 'GOOGLE_SLAs_CLOUD_WORKSHEET'
        else:
            target_ws_key = 'GOOGLE_SLAs_HTC_WORKSHEET'

        worksheet = init_GWorkSheet(self.env, target_ws_key)
        if not worksheet and not dry_run:
            return

        slas = self.fetch_active_slas()
        
        if dry_run:
             print(colourise("yellow", "\n[DRY-RUN]"), f"Found {len(slas)} active SLAs.")
             return

        # Ensure base header "VO" in A1
        headers = worksheet.row_values(1)
        if not headers or "VO" not in headers[0]:
             print(colourise("cyan", "[INFO]"), "Initializing header in A1...")
             worksheet.update('A1', [['VO']], value_input_option='RAW')

        # Check Period Column
        period_col, found = self.get_period_col_position(worksheet, reporting_period)
        if not found:
            print(colourise("cyan", "\n[INFO]"), f"Adding period {reporting_period} at column {period_col}")
            worksheet.insert_cols([[reporting_period]], col=period_col, value_input_option='RAW', inherit_from_before=True)
        else:
            print(colourise("green", "\n[INFO]"), f"Period found at column {period_col}")
        
        # 1. Ensure all needed VO rows exist in batch
        print(colourise("cyan", "[INFO]"), "Syncing VO rows (Batch Mode)...")
        vos_to_process = []
        for vo in slas:
            if self.env['ACCOUNTING_SCOPE'] in vo['Type'] and \
               self.env['DATE_FROM'] >= vo['SLA_start'] and \
               self.env['DATE_TO'] <= vo['SLA_end']:
                vos_to_process.append(vo)
        
        vos_to_process.sort(key=lambda x: x['Name'])
        
        all_col1 = worksheet.col_values(1)
        new_vos = [vo for vo in vos_to_process if vo['Name'] not in all_col1]
        
        if new_vos:
            print(colourise("cyan", "[INFO]"), f"Adding {len(new_vos)} new VO rows...")
            insert_row_idx = 2
            # find first row > new_vos[0]
            for i, val in enumerate(all_col1):
                if i == 0: continue # Skip VO header
                if val == "": break
                if val > new_vos[0]['Name']:
                    insert_row_idx = i + 1
                    break
            else:
                insert_row_idx = len(all_col1) + 1
            
            row_data = [[vo['Name']] for vo in new_vos]
            try:
                worksheet.insert_rows(row_data, row=insert_row_idx, value_input_option='RAW')
                print(colourise("green", "[SUCCESS]"), f"Inserted {len(new_vos)} rows.")
            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Failed to batch insert rows: {e}")
        
        total_cpu = 0
        print(colourise("green", "\n[INFO]"), "Fetching accounting records...")
        
        cells_to_update = []
        for vo in vos_to_process:
            data = self.fetch_vo_accounting(vo['Name'])
            if data:
                for record in data:
                    if "Total" in record['id']:
                        val = record['Total']
                        total_cpu += val
                        print(f"- {vo['Name']}: {val}")
                        try:
                            vo_row, found = self.get_vo_row_position(worksheet, vo['Name'])
                            if found:
                                cells_to_update.append(gspread.Cell(vo_row, period_col, val))
                            else:
                                vo_row = self.ensure_vo_row(worksheet, vo['Name'])
                                cells_to_update.append(gspread.Cell(vo_row, period_col, val))
                        except Exception as e:
                            print(f"Error buffering {vo['Name']}: {e}")
        
        # Update Total? SLAs usually don't have a sum, but our code tried one.
        # If there is a TOTAL row, find it.
        try:
             total_row_idx = None
             current_col1 = worksheet.col_values(1)
             if "TOTAL" in current_col1:
                 total_row_idx = current_col1.index("TOTAL") + 1
                 cells_to_update.append(gspread.Cell(total_row_idx, period_col, total_cpu))
        except:
             pass

        # Perform batch update
        if cells_to_update:
            print(colourise("cyan", "[INFO]"), f"Performing batch update of {len(cells_to_update)} cells...")
            try:
                worksheet.update_cells(cells_to_update, value_input_option='RAW')
            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Failed batch update: {e}")

        try:
            worksheet.insert_note("A1", f"Last update: {datetime.datetime.now()}")
        except:
            pass

if __name__ == "__main__":
    app = SLAsAccounting()
    app.main()
