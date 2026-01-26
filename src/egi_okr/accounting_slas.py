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

    def get_cell_position(self, worksheet, accounting_period, is_col=False):
        # Find the row position for the reporting period in Column A.
        pos = 2
        try:
            cell = worksheet.find(accounting_period)
            if cell:
                return cell.row, True
        except:
            pass
        
        values_list = worksheet.col_values(1)
        if len(values_list) > 1:
            for header in values_list:
                if "Period" not in header:
                    if header == "":
                        break
                    if header < accounting_period:
                        pos += 1
                    else:
                        break
        return pos, False

    def get_vo_col_position(self, worksheet, vo_name):
        # Header is Row 1. find the column for the VO.
        try:
            cell = worksheet.find(vo_name)
            if cell and cell.row == 1:
                return cell.col, True
        except:
            pass

        pos = 2
        values_list = worksheet.row_values(1)
        
        if len(values_list) > 1:
             for header in values_list:
                 if "Period" not in header:
                     if header == "":
                         break
                     if header < vo_name:
                         pos += 1
                     else:
                         break
        
        return pos, False

    def ensure_vo_column(self, worksheet, vo_name):
        """Find or insert VO column."""
        vo_col, found = self.get_vo_col_position(worksheet, vo_name)
        
        if not found:
             print(colourise("green", "[INFO]"), f"Adding '{vo_name}' at column: {vo_col}")
             worksheet.insert_cols([[vo_name]], vo_col, value_input_option='RAW', inherit_from_before=False)
        
        return vo_col



    def fetch_slas_from_api(self):
        """Fetch VOs from Operations Portal API as a fallback for SLA list."""
        print(colourise("yellow", "[INFO]"), "Fetching VOs from API to use as SLA list...")
        
        vos_stats = get_VOs_stats(self.env)
        slas = []
        
        for vo in vos_stats:
            # Only include Production VOs? Or all? User said "populate list of SLA from API"
            # get_VOs_stats filters for production VOs usually or returns status?
            # get_VOs_stats in operations.py returns dict with 'name', 'status' isn't explicitly in the dict returned by get_VOs_stats!
            # Wait, let's check get_VOs_stats output structure in operations.py.
            # It returns: name, scope, url, users, active_members... NO STATUS.
            # But the loop in get_VOs_stats iterates `response.get('data', [])`.
            # The API /vo-list returns filtered list or all?
            # It usually returns valid VOs.
            
            # We will assume all returned VOs are potential SLA candidates.
            # We map them to the structure expected by main()
            
            slas.append({
                "Customer": vo['name'], # Use VO name as customer
                "Name": vo['name'],
                "CPU/h": 0,
                # Set start/end to current period to ensure they are picked up
                "SLA_start": self.env['DATE_FROM'],
                "SLA_end": self.env['DATE_TO'],
                "Active": "Y",
                "Type": "egi, cloud" # Assume check both
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
                
                # Determine indices based on fixed SLA report structure.
                # index 10: VO Name, index 6: Status, index 12: Cloud, index 16: EGI/HTC.
                
                for value in values:
                     # Skip header row and short lines.
                     if len(value) < 17 or "VO name" in value[10]:
                         continue
        
                     status = value[6]
                     vo_name = value[10]
                     
                     # Classify SLA type based on Cloud and EGI service markers.
                     if "FINALIZED" in status:
                         sla_type = ""
                         v12 = value[12] # Cloud marker
                         v16 = value[16] # EGI marker
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

        # Fallback to API if no SLAs found in sheet
        if not vos:
            print(colourise("yellow", "[WARN]"), "No active SLAs found in spreadsheet (or tab missing).")
            vos = self.fetch_slas_from_api()
            
        return vos

    def fetch_vo_accounting(self, vo_name):
        # EGI Accounting Portal has migrated to a new Django-based system.
        # We use the REST-like URL structure for single VO accounting.
        # Pattern: {SERVER}/{SCOPE}/{METRIC}/REGION/Year/{DATE_FROM}/{DATE_TO}/custom-{VO}/{LOCAL_JOBS}/{DATA_SELECTOR}/
        
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

        # Determine correct worksheet key based on scope
        scope = self.env.get('ACCOUNTING_SCOPE', '')
        if 'cloud' in scope:
            target_ws_key = 'GOOGLE_SLAs_CLOUD_WORKSHEET'
        else:
            target_ws_key = 'GOOGLE_SLAs_HTC_WORKSHEET'

        # This target sheet is in the spreadsheet defined by GOOGLE_SHEET_NAME.
        worksheet = init_GWorkSheet(self.env, target_ws_key)
        if not worksheet and not dry_run:
            return

        # Fetch SLAs
        slas = self.fetch_active_slas()
        
        if dry_run:
             print(colourise("yellow", "\n[DRY-RUN]"), f"Found {len(slas)} active SLAs.")
             # We can't really simulate the full accounting loop easily without mock data or making requests
             # For dry run, lets just print what SLAs we would check
             print("SLAs to be checked:")
             for vo in slas:
                  print(f" - {vo['Name']} ({vo['Type']})")
             return

        # Check Period Row
        period_pos, found = self.get_cell_position(worksheet, reporting_period)
        if not found:
            print(colourise("cyan", "\n[INFO]"), f"Adding period {reporting_period} at row {period_pos}")
            worksheet.insert_row([reporting_period, 0], index=period_pos)
        else:
            print(colourise("green", "\n[INFO]"), f"Period found at row {period_pos}")
             
        total_cpu = 0
        
        print(colourise("green", "\n[INFO]"), "Fetching accounting records...")
        
        # Iterate SLAs
        cells_to_update = []
        for vo in slas:
            # Check if the reporting period is within the SLA start and end dates.
            # Note: Assumes compatible date string formats.
             
            if self.env['ACCOUNTING_SCOPE'] in vo['Type'] and \
               self.env['DATE_FROM'] >= vo['SLA_start'] and \
               self.env['DATE_TO'] <= vo['SLA_end']:
                
                data = self.fetch_vo_accounting(vo['Name'])
                if data:
                    for record in data:
                        if "Total" in record['id']:
                            val = record['Total']
                            total_cpu += val
                              
                            # Buffer update
                            print(f"- {vo['Name']}: {val}")
                            try:
                                vo_col = self.ensure_vo_column(worksheet, vo['Name'])
                                cells_to_update.append(gspread.Cell(period_pos, vo_col, val))
                            except Exception as e:
                                print(f"Error buffering {vo['Name']}: {e}")
        
        # Update Total
        print(colourise("cyan", "\n[REPORT]"), f"Total CPU: {total_cpu}")
        
        try:
             total_cell = worksheet.find("TOTAL")
             if total_cell:
                 cells_to_update.append(gspread.Cell(period_pos, total_cell.col, total_cpu))
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
