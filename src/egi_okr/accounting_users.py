
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

import json
import gspread
from .base_accounting import BaseAccounting
from .utils import colourise, handle_exception
from .operations import get_VOs_stats, get_VOs_report

class UsersAccounting(BaseAccounting):
    def __init__(self, env=None):
        super().__init__(env)

    def process_metric_sheet(self, worksheet, vos_list, metric_key, metric_name):
        """Generic method to process a metric sheet (active users, registered, or total)."""
        self.apply_standard_formatting(worksheet)
        
        # 1. Fetch bulk data once
        all_rows = worksheet.get_all_values()
        headers = all_rows[0] if all_rows else []
        existing_names = [r[0] if r else "" for r in all_rows]
        
        # 2. Find or create period column
        period_col = self.get_period_column(worksheet, headers=headers)
        
        cells_to_update = []
        remaining_vos = []

        # 3. Update existing VOs
        for vo in vos_list:
            name = vo['name']
            metric_value = vo.get(metric_key, 0)
            
            if name in existing_names:
                row_idx = existing_names.index(name) + 1
                cells_to_update.append(gspread.Cell(row_idx, period_col, metric_value))
            else:
                remaining_vos.append((name, metric_value))

        # 4. Batch insert new VOs
        if remaining_vos:
            remaining_vos.sort(key=lambda x: x[0])
            start_row = self.get_item_row(worksheet, remaining_vos[0][0], start_row=2, all_values=all_rows)
            
            print(f"\tInserting {len(remaining_vos)} new VOs into {metric_name} sheet at row {start_row}...")
            worksheet.insert_rows([[vo[0]] for vo in remaining_vos], row=start_row)
            
            for i, (name, value) in enumerate(remaining_vos):
                row = start_row + i
                cells_to_update.append(gspread.Cell(row, period_col, value))

        if cells_to_update:
            print(f"\tPerforming batch update of {len(cells_to_update)} cells in {metric_name} sheet...")
            worksheet.update_cells(cells_to_update, value_input_option='RAW')

    def run_vo_reports_logic(self, dry_run=False):
        """Unified logic from legacy vo_reports.py - Created/Deleted VO counts."""
        worksheet = self.init_worksheet('GOOGLE_VOS_REPORT_WORKSHEET')
        if not worksheet: return

        vos_report = get_VOs_report(self.env, session=self.session)
        if dry_run:
            print(colourise("yellow", "[DRY-RUN]"), f"Fetched Created/Deleted reports for {len(vos_report)} status types.")
            return

        # Legacy logic: row-based period reports (A=Period, B=Total, C=Deleted, D=Prod, E=VO List)
        total = sum([int(i['count']) for i in vos_report])
        total_deleted = sum([int(i['count']) for i in vos_report if "Deleted" in i.get('status', '')])
        total_prod = sum([int(i['count']) for i in vos_report if "Production" in i.get('status', '')])
        vos_string = ', '.join([str(e['vos']) for e in vos_report]) if vos_report else '-'

        # Setup Sheet (Single Read)
        all_rows = worksheet.get_all_values()
        existing_periods = [r[0] if r else "" for r in all_rows]
        
        if self.accounting_period in existing_periods:
            row_idx = existing_periods.index(self.accounting_period) + 1
            worksheet.update_cells([
                gspread.Cell(row_idx, 2, total),
                gspread.Cell(row_idx, 3, total_deleted),
                gspread.Cell(row_idx, 4, total_prod),
                gspread.Cell(row_idx, 5, vos_string)
            ], value_input_option='RAW')
        else:
            row_idx = self.get_item_row(worksheet, self.accounting_period, first_col_index=1, all_values=all_rows, descending=True)
            worksheet.insert_row([self.accounting_period, total, total_deleted, total_prod, vos_string], index=row_idx)

    def run(self, dry_run=False):
        print(f"\n[*] Module: Users (Standardized)")
        
        # Always fetch stats for reporting/dry-run
        vos_stats = get_VOs_stats(self.env, session=self.session)
        
        if dry_run:
            print(colourise("yellow", "[DRY-RUN]"), f"Fetched stats for {len(vos_stats)} VOs.")
        else:
            # 1. Active Users sheet (users per period)
            worksheet_active = self.init_worksheet('GOOGLE_VOS_WORKSHEET')
            if worksheet_active:
                print(colourise("cyan", "\n[INFO]"), "Processing VOs - Active Users sheet...")
                self.process_metric_sheet(worksheet_active, vos_stats, 'users', 'Active Users')
                self.update_timestamp(worksheet_active)
            else:
                print(colourise("red", "[ABORT]"), "VOs Worksheet not found. Skipping active users.")

            # 2. Registered Users sheet (active_members per period)
            worksheet_registered = self.init_worksheet('GOOGLE_VOS_REGISTERED_WORKSHEET')
            if worksheet_registered:
                print(colourise("cyan", "\n[INFO]"), "Processing VOs - Registered Users sheet...")
                self.process_metric_sheet(worksheet_registered, vos_stats, 'active_members', 'Registered Users')
                self.update_timestamp(worksheet_registered)
            else:
                print(colourise("yellow", "[WARN]"), "VOs-Registered Worksheet not found. Skipping registered users.")

            # 3. Total Users sheet (total_members per period)
            worksheet_total = self.init_worksheet('GOOGLE_VOS_TOTAL_WORKSHEET')
            if worksheet_total:
                print(colourise("cyan", "\n[INFO]"), "Processing VOs - Total Users sheet...")
                self.process_metric_sheet(worksheet_total, vos_stats, 'total_members', 'Total Users')
                self.update_timestamp(worksheet_total)
            else:
                print(colourise("yellow", "[WARN]"), "VOs-Total Worksheet not found. Skipping total users.")

        # 4. Unified Report Logic (Report sheet - legacy vo_reports.py)
        self.run_vo_reports_logic(dry_run)

if __name__ == "__main__":
    UsersAccounting().run()
