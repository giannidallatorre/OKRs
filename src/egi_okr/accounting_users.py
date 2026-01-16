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
import time
import requests
import warnings
import gspread
from gspread.exceptions import GSpreadException
from .utils import get_env_settings, handle_exception, init_GWorkSheet, colourise, format_reporting_period
from .operations import get_VOs_stats

class UsersAccounting:
    def __init__(self, env=None):
        self.env = env if env is not None else get_env_settings()

    def get_column_by_label(self, worksheet, label):
        """Find column index by its header label. Returns None if not found."""
        try:
            cell = worksheet.find(label)
            return cell.col if cell else None
        except:
            return None

    def update_headers(self, worksheet, accounting_period):
        """Ensure the reporting period column exists and is correctly positioned."""
        existing_col = self.get_column_by_label(worksheet, accounting_period)
        
        if existing_col:
            print(f"\tThe header '{accounting_period}' is *already* in the Worksheet (column {existing_col})")
            return existing_col

        # If not found, find where to insert
        headers = worksheet.row_values(1)
        y_pos = 2  # Start after VO column
        
        if headers:
            for header in headers:
                if "VO" not in header and "Users" not in header:
                    if header < accounting_period:
                        y_pos += 1
                    else:
                        break
        
        print(f"Adding '{accounting_period}' at column: {y_pos}")
        worksheet.insert_cols(
            [[accounting_period]], 
            y_pos, 
            value_input_option='RAW', 
            inherit_from_before=True
        )
        return y_pos

    def get_vo_position(self, worksheet, vo_name):
        """Find the lexicographical row position for a new VO."""
        all_values = worksheet.get_all_values()
        row = 3 # Starting row for data
        if len(all_values) > 2:
            # First row is headers, Second row is usually TOTAL/Timestamp or similar
            # Data usually starts from row 3
            for values in all_values[2:]: # Check from row 3
                vo_in_row = values[0] if values else ""
                if "TOTAL" not in vo_in_row.upper():
                    if vo_in_row < vo_name:
                        row += 1
                    else:
                        break
        return row

    def update_vos(self, worksheet, vos_list, accounting_period):
        # Format headers
        worksheet.format("A1:B1", {
            "backgroundColor": {"red": 55.0, "green": 15.0, "blue": 10.0},
            "horizontalAlignment": "LEFT",
            "textFormat": {"fontSize": 11, "bold": True}
        })
        worksheet.format("A2:Z300", { # Expanded range
            "horizontalAlignment": "RIGHT",
            "textFormat": {"fontSize": 10}
        })

        print(colourise("cyan", "\n[INFO]"), "\tUpdating statistics of existing VOs..")

        
        def safe_find_col(label):
            try:
                cell = worksheet.find(label)
                return cell.col if cell else None
            except:
                return None
        
        period_col = safe_find_col(accounting_period)
        reg_users_col = safe_find_col('Registered Users')
        total_users_col = safe_find_col('Total Users')

        if not period_col or not reg_users_col or not total_users_col:
             print(colourise("red", "[ERROR]"), "Missing required columns in worksheet")
             return

        # Get all VO names in column 1 to avoid repeated findall
        all_col1_values = worksheet.col_values(1)
        
        # 1. Update existing VOs
        remaining_vos = []
        for vo in vos_list:
            vo_name = vo['name']
            
            # Find row index (1-based)
            try:
                row_index = None
                if vo_name in all_col1_values:
                    # find index of first occurrence
                    row_index = all_col1_values.index(vo_name) + 1
                
                if not row_index:
                     remaining_vos.append(vo)
                     continue
                
                worksheet.update_cell(row_index, period_col, vo['users'])
                worksheet.update_cell(row_index, reg_users_col, vo['active_members'])
                worksheet.update_cell(row_index, total_users_col, vo['total_members'])
                
                if self.env.get('LOG') == "DEBUG":
                     print(colourise("green", "[LOG]"), f"Updated {vo_name}")

            except Exception as e:
                # Handle quota limit
                if "Quota exceeded" in str(e):
                    print(colourise("red", "[WARNING]"), "Quota exceeded, waiting 120s...")
                    time.sleep(120)
                    remaining_vos.append(vo) 
                else:
                    print(colourise("red", "[ERROR]"), f"Error updating {vo_name}: {e}")

        # 2. Insert new VOs
        if remaining_vos:
            print(colourise("cyan", "\n[INFO]"), "\tInserting new VOs..")
            
            # Re-fetch header positions as cols might have shifted? No, we only inserted cols at start.
            # But get_vo_position needs updated sheet data if we insert rows.
            
            for vo in remaining_vos:
                try:
                    row_index = self.get_vo_position(worksheet, vo['name'])
                    print(f"Insert {vo['name']} at row {row_index}")
                    
                    # Insert row
                    worksheet.insert_row(['', ''], index=row_index)
                    
                    worksheet.update_cell(row_index, 1, vo['name'])
                    worksheet.update_cell(row_index, period_col, vo['users'])
                    worksheet.update_cell(row_index, reg_users_col, vo['active_members'])
                    worksheet.update_cell(row_index, total_users_col, vo['total_members'])
                    
                except Exception as e:
                    if "Quota exceeded" in str(e):
                        print(colourise("red", "[WARNING]"), "Quota exceeded, waiting 120s...")
                        time.sleep(120)
                        print(colourise("red", "[ERROR]"), f"Error inserting {vo['name']}: {e}")

        if remaining_vos:
            print(colourise("cyan", "[INFO]"), f"Processed/Added {len(remaining_vos)} new VOs.")

    def run(self):
        dt = datetime.datetime.now()
        timestamp = dt.strftime("%d-%m-%Y %H:%M:%S")
        
        print(f"\nLog Level = {colourise('cyan', self.env.get('LOG', 'INFO'))}")
        
        accounting_period = format_reporting_period(self.env)
        print(colourise("cyan", "\n[INFO]"), f"\tReporting Period: '{accounting_period}'")

        if accounting_period in ["UNKNOWN_PERIOD", "INVALID_PERIOD"]:
            print(colourise("red", "[ABORT]"), "Cannot proceed with invalid or unknown reporting period.")
            return

        worksheet = init_GWorkSheet(self.env, 'GOOGLE_VOS_WORKSHEET')
        if not worksheet:
             return

        self.update_headers(worksheet, accounting_period)

        vos_stats = get_VOs_stats(self.env)
        if self.env.get('LOG') == "DEBUG":
            print(json.dumps(vos_stats, indent=4))

        self.update_vos(worksheet, vos_stats, accounting_period)
        
        worksheet.insert_note("A1", "Last Update on: " + timestamp)


if __name__ == "__main__":
    app = UsersAccounting()
    app.run()
