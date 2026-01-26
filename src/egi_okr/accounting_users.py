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
        """Ensure all required columns exist and are correctly positioned."""
        # 1. Ensure base columns exist
        headers = worksheet.row_values(1)
        if not headers:
            headers = ["VO", "Registered Users", "Total Users"]
            worksheet.update('A1:C1', [headers])
        else:
            if "VO" not in headers:
                worksheet.insert_cols([["VO"]], 1, value_input_option='RAW')
                headers = worksheet.row_values(1)
            
            if "Registered Users" not in headers:
                # Find last "static" column or insert at end
                worksheet.insert_cols([["Registered Users"]], len(headers) + 1, value_input_option='RAW')
                headers = worksheet.row_values(1)

            if "Total Users" not in headers:
                worksheet.insert_cols([["Total Users"]], len(headers) + 1, value_input_option='RAW')
                headers = worksheet.row_values(1)

        # 2. Ensure period column exists
        existing_col = self.get_column_by_label(worksheet, accounting_period)
        if existing_col:
            print(f"\tThe header '{accounting_period}' is *already* in the Worksheet (column {existing_col})")
            return existing_col

        # Find where to insert period (between base columns and user columns)
        # We want: [VO] [Period1] [Period2] ... [Registered Users] [Total Users]
        reg_col = self.get_column_by_label(worksheet, "Registered Users")
        y_pos = reg_col # Insert before Registered Users
        
        # Sort among existing periods
        current_headers = worksheet.row_values(1)
        for i, header in enumerate(current_headers):
            if i == 0: continue # Skip VO
            if header == "Registered Users": break
            if header < accounting_period:
                y_pos = i + 2 # Keep searching
            else:
                y_pos = i + 1
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
             # This should not happen now with updated update_headers, but just in case
             print(colourise("red", "[ERROR]"), f"Missing required columns in worksheet after header update. P:{period_col} R:{reg_users_col} T:{total_users_col}")
             return

        # Get all VO names in column 1 to avoid repeated findall
        all_rows = worksheet.get_all_values()
        all_col1_values = [r[0] if r else "" for r in all_rows]
        
        cells_to_update = []
        
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
                
                # Buffer updates
                cells_to_update.append(gspread.Cell(row_index, period_col, vo['users']))
                cells_to_update.append(gspread.Cell(row_index, reg_users_col, vo['active_members']))
                cells_to_update.append(gspread.Cell(row_index, total_users_col, vo['total_members']))
                
                if self.env.get('LOG') == "DEBUG":
                     print(colourise("green", "[LOG]"), f"Buffered update for {vo_name}")

            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Error preparing update for {vo_name}: {e}")

        # 2. Insert new VOs
        if remaining_vos:
            print(colourise("cyan", "\n[INFO]"), "\tInserting new VOs..")
            
            for vo in remaining_vos:
                try:
                    row_index = self.get_vo_position(worksheet, vo['name'])
                    print(f"Insert {vo['name']} at row {row_index}")
                    
                    # We still have to insert rows one by one, but we can buffer the cell data
                    worksheet.insert_row([vo['name']], index=row_index)
                    
                    # Update cell list for the new row (columns might have shifted? No, we only insert rows below/above)
                    cells_to_update.append(gspread.Cell(row_index, period_col, vo['users']))
                    cells_to_update.append(gspread.Cell(row_index, reg_users_col, vo['active_members']))
                    cells_to_update.append(gspread.Cell(row_index, total_users_col, vo['total_members']))
                    
                except Exception as e:
                    if "Quota exceeded" in str(e):
                        print(colourise("red", "[WARNING]"), "Quota exceeded during row insertion, waiting 60s...")
                        time.sleep(60)
                    print(colourise("red", "[ERROR]"), f"Error inserting {vo['name']}: {e}")

        # 3. Perform batch update
        if cells_to_update:
            print(colourise("cyan", "[INFO]"), f"Performing batch update of {len(cells_to_update)} cells...")
            try:
                # Group updates to stay under quota if possible, though update_cells is already a batch
                worksheet.update_cells(cells_to_update, value_input_option='RAW')
            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Failed batch update: {e}")

        if remaining_vos:
            print(colourise("cyan", "[INFO]"), f"Processed/Added {len(remaining_vos)} new VOs.")

    def run(self, dry_run=False):
        dt = datetime.datetime.now()
        timestamp = dt.strftime("%d-%m-%Y %H:%M:%S")
        
        print(f"\nLog Level = {colourise('cyan', self.env.get('LOG', 'INFO'))}")
        
        accounting_period = format_reporting_period(self.env)
        print(colourise("cyan", "\n[INFO]"), f"\tReporting Period: '{accounting_period}'")

        if accounting_period in ["UNKNOWN_PERIOD", "INVALID_PERIOD"]:
            print(colourise("red", "[ABORT]"), "Cannot proceed with invalid or unknown reporting period.")
            return

        worksheet = init_GWorkSheet(self.env, 'GOOGLE_VOS_WORKSHEET')
        if not worksheet and not dry_run:
             return

        if not dry_run:
            self.update_headers(worksheet, accounting_period)

        vos_stats = get_VOs_stats(self.env)
        if self.env.get('LOG') == "DEBUG":
            print(json.dumps(vos_stats, indent=4))

        if dry_run:
            print(colourise("yellow", "\n[DRY-RUN]"), f"Fetching stats for {len(vos_stats)} VOs.")
            # Sample output
            print(f"Sample data (first 3):")
            for vo in vos_stats[:3]:
                print(f" - {vo['name']}: {vo['users']} users, {vo['active_members']} active, {vo['total_members']} total")
        else:
            self.update_vos(worksheet, vos_stats, accounting_period)
            
            try:
                worksheet.insert_note("A1", "Last Update on: " + timestamp)
            except:
                pass


if __name__ == "__main__":
    app = UsersAccounting()
    app.run()
