
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
import gspread
from .base_accounting import BaseAccounting
from .utils import handle_exception, colourise
from .jira import get_service_orders

class OrdersAccounting(BaseAccounting):
    def __init__(self, env=None):
        super().__init__(env)

    def parse_service_name(self, details):
        import re
        try:
             # Look for "service":"Name" in the JSON-like details string
             match = re.search(r'"service":"([^"]+)"', details)
             if match:
                 name = match.group(1)
                 # Map some common aliases if needed, or just return
                 return name
        except: pass
        return "Unknown"

    def process_orders(self, jira_orders):
        buckets = {
            "Cloud Compute": 0, "Cloud Container Compute": 0, "High-Throughput Compute": 0,
            "Online Storage": 0, "Archive Storage": 0, "Check-in": 0, "Training Infrastructure": 0
        }
        for order in jira_orders:
            # Custom field 10711 contains service details
            details = order.get('fields', {}).get('customfield_10711', '')
            name = self.parse_service_name(details).lower()
            
            if 'cloud compute' in name: buckets["Cloud Compute"] += 1
            elif 'container compute' in name: buckets["Cloud Container Compute"] += 1
            elif 'high-throughput compute' in name: buckets["High-Throughput Compute"] += 1
            elif 'online storage' in name: buckets["Online Storage"] += 1
            elif 'archive storage' in name: buckets["Archive Storage"] += 1
            elif 'check-in' in name: buckets["Check-in"] += 1
            elif 'training infrastructure' in name: buckets["Training Infrastructure"] += 1
        return buckets
    def run(self, dry_run=False):
        print(f"\n[*] Module: Orders (Standardized)")
        worksheet = self.init_worksheet('GOOGLE_ORDERS_WORKSHEET')
        
        # Always fetch data
        orders = get_service_orders(self.env)
        buckets = self.process_orders(orders)
        
        if dry_run:
            status = "(No Worksheet)" if not worksheet else ""
            print(f"\tSummary: {len(orders)} orders processed into {len(buckets)} buckets. {status}")
            return

        if not worksheet:
            print(colourise("red", "[ABORT]"), "Orders Worksheet not found.")
            return

        # Setup Orientation (Single Read)
        all_values = worksheet.get_all_values()
        headers = all_values[0] if all_values else []
        
        period_col = self.get_period_column(worksheet, headers=headers)
        self.apply_standard_formatting(worksheet)
        
        cells = []
        for i, (name, count) in enumerate(buckets.items()):
            row = i + 2
            cells.append(gspread.Cell(row, 1, name))
            cells.append(gspread.Cell(row, period_col, count))

        print(f"\tPerforming batch update for {len(cells)} service cells...")
        worksheet.update_cells(cells, value_input_option='RAW')
        self.update_timestamp(worksheet)

if __name__ == "__main__":
    OrdersAccounting().run()
