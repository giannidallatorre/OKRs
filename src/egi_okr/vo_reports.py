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
from .utils import get_env_settings, handle_exception, init_GWorkSheet, colourise
from .operations import get_VOs_report

class VOsReports:
    def __init__(self, env=None):
        self.env = env if env is not None else get_env_settings()

    def get_cell_position(self, worksheet, reporting_period):
        pos = 2
        found = False
        values_list = worksheet.col_values(1)
        if len(values_list) > 1:
            for header in values_list:
                if "Period" not in header:
                    if header == reporting_period or header == "":
                        found = True
                        break
                    if header < reporting_period:
                        pos += 1
        return pos, found

    def update_worksheet(self, worksheet, reporting_period, vos_report):
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Format
        worksheet.format("A1:E1", {
            "backgroundColor": {"red": 55.0, "green": 15.0, "blue": 10.0},
            "horizontalAlignment": "LEFT",
            "textFormat": {"fontSize": 11, "bold": True}
        })
        worksheet.format("A2:E100", {
            "horizontalAlignment": "RIGHT",
            "textFormat": {"fontSize": 11}
        })

        total = 0
        total_deleted = 0
        total_production = 0
        
        for item in vos_report:
             count = int(item['count'])
             total += count
             status = item.get('status', '') 
             # Accumulate counts based on VO status.
             # status "Deleted" -> total_deleted += count
             # status "Production" -> total_production += count
             
             if "Deleted" in status:
                 total_deleted += count
             if "Production" in status:
                 total_production += count

        # Flatten VOs list into a comma-separated string.
        # Format: 'VO name(P)' where (P) potentially indicates Production.
        vos_string = ', '.join([str(elem['vos']) for elem in vos_report]) if vos_report else '-'

        # Update or Insert
        try:
             # Find period row
             found_period = worksheet.findall(reporting_period)
             cell = None
             for c in found_period:
                 if c.col == 1:
                     cell = c
                     break
             
             if cell:
                 # Update
                 worksheet.update_cell(cell.row, 2, total)
                 worksheet.update_cell(cell.row, 3, total_deleted)
                 worksheet.update_cell(cell.row, 4, total_production)
                 worksheet.update_cell(cell.row, 5, vos_string)
                 print(colourise("cyan", "[INFO]"), f"Updated report for {reporting_period}")
             else:
                 # Insert
                 pos, _ = self.get_cell_position(worksheet, reporting_period)
                 print(colourise("cyan", "\n[INFO]"), f"Adding {reporting_period} at row: {pos}")
                 
                 body = [
                     reporting_period,
                     total,
                     total_deleted,
                     total_production,
                     vos_string
                 ]
                 worksheet.insert_row(body, index=pos, inherit_from_before=True)
                 print(colourise("cyan", "[INFO]"), f"Inserted report for {reporting_period}")

             worksheet.insert_note("A1", "Last update on: " + timestamp)

        except Exception as e:
            handle_exception(e, self.env)

    def run(self):
        log_level = self.env.get('LOG', 'INFO')
        print(f"\nLog Level = {colourise('cyan', log_level)}")
        
        if log_level == "DEBUG":
            print("\n- Environment settings details hidden -")

        reporting_period = f"{self.env['DATE_FROM'][0:4]}.{self.env['DATE_FROM'][-2:]}-{self.env['DATE_TO'][-2:]}"
        print(colourise("cyan", "\n[INFO]"), f"Reporting Period: {reporting_period}")

        # Use the configured worksheet for VO reporting.
        worksheet = init_GWorkSheet(self.env, 'GOOGLE_VOS_REPORT_WORKSHEET')
        if not worksheet:
            return

        vos_report = get_VOs_report(self.env)
        
        if log_level == "DEBUG":
             print(colourise("green", "\n[LOG]"), f"VOs Report:\n{json.dumps(vos_report, indent=4)}")

        self.update_worksheet(worksheet, reporting_period, vos_report)

if __name__ == "__main__":
    app = VOsReports()
    app.run()
