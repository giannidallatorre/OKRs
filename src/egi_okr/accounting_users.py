
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

    def update_headers(self, worksheet, headers=None):
        """Standardize headers for the Users sheet."""
        if headers is None:
            headers = worksheet.row_values(1)
            
        if not headers:
            headers = ["VO", "Registered Users", "Total Users"]
            worksheet.update('A1:C1', [headers])
        else:
            if "VO" not in headers:
                worksheet.insert_cols([["VO"]], 1, value_input_option='RAW')
            if "Registered Users" not in headers:
                worksheet.insert_cols([["Registered Users"]], len(headers) + 1, value_input_option='RAW')
            if "Total Users" not in headers:
                worksheet.insert_cols([["Total Users"]], len(headers) + 1, value_input_option='RAW')

        # Find period column position (between VO and User counts)
        return self.get_period_column(worksheet, start_col=2, static_headers=["Registered Users", "Total Users"], headers=headers)

    def process_vos(self, worksheet, vos_list, period_col):
        """Update existing VOs and batch-insert new ones."""
        self.apply_standard_formatting(worksheet)
        
        # 1. Fetch bulk data once
        all_rows = worksheet.get_all_values()
        headers = all_rows[0] if all_rows else []
        existing_names = [r[0] if r else "" for r in all_rows]
        
        reg_users_col = self.get_column_by_label(worksheet, 'Registered Users', headers=headers)
        total_users_col = self.get_column_by_label(worksheet, 'Total Users', headers=headers)

        cells_to_update = []
        remaining_vos = []

        # 2. Update existing
        for vo in vos_list:
            name = vo['name']
            if name in existing_names:
                row_idx = existing_names.index(name) + 1
                cells_to_update.append(gspread.Cell(row_idx, period_col, vo['users']))
                cells_to_update.append(gspread.Cell(row_idx, reg_users_col, vo['active_members']))
                cells_to_update.append(gspread.Cell(row_idx, total_users_col, vo['total_members']))
            else:
                remaining_vos.append(vo)

        # 3. Batch insert new
        if remaining_vos:
            remaining_vos.sort(key=lambda x: x['name'])
            start_row = self.get_item_row(worksheet, remaining_vos[0]['name'], start_row=3, all_values=all_rows)
            
            print(f"\tInserting {len(remaining_vos)} new VOs at row {start_row}...")
            worksheet.insert_rows([[vo['name']] for vo in remaining_vos], row=start_row)
            
            for i, vo in enumerate(remaining_vos):
                row = start_row + i
                cells_to_update.append(gspread.Cell(row, period_col, vo['users']))
                cells_to_update.append(gspread.Cell(row, reg_users_col, vo['active_members']))
                cells_to_update.append(gspread.Cell(row, total_users_col, vo['total_members']))

        if cells_to_update:
            print(f"\tPerforming batch update of {len(cells_to_update)} cells...")
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
        
        # 1. Main VO stats (VOs sheet)
        worksheet = self.init_worksheet('GOOGLE_VOS_WORKSHEET')
        
        # Always fetch stats for reporting/dry-run
        vos_stats = get_VOs_stats(self.env, session=self.session)
        
        if worksheet:
            # Setup headers (Single Read)
            headers = worksheet.row_values(1)
            period_col = self.update_headers(worksheet, headers=headers)
            
            if dry_run:
                print(colourise("yellow", "[DRY-RUN]"), f"Fetched stats for {len(vos_stats)} VOs.")
            else:
                self.process_vos(worksheet, vos_stats, period_col)
                self.update_timestamp(worksheet)
        else:
            if dry_run:
                print(colourise("yellow", "[DRY-RUN]"), f"Fetched stats for {len(vos_stats)} VOs (No Worksheet).")
            else:
                print(colourise("red", "[ABORT]"), "VOs Worksheet not found. Skipping main stats.")

        # 2. Unified Report Logic (Report sheet - legacy vo_reports.py)
        self.run_vo_reports_logic(dry_run)

if __name__ == "__main__":
    UsersAccounting().run()
