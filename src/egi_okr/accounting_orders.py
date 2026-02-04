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

import re
import json
import time
import gspread
from .utils import get_env_settings, handle_exception, init_GWorkSheet, colourise, format_reporting_period
from .jira import get_service_orders

class OrdersAccounting:
    def __init__(self, env=None):
        self.env = env if env is not None else get_env_settings()
        self.egi_services = [
            "EGI Cloud Compute",
            "EGI Cloud Container Compute",
            "EGI High-Throughput Compute",
            "EGI Software Distribution",
            "EGI Workload Manager",
            "EGI Infrastructure Manager",
            "EGI Online Storage",
            "EGI Data Transfer",
            "EGI DataHub",
            "EGI Check-In",
            "EGI Notebooks",
            "EGI Replay",
            "EGI FitSM Training",
            "EGI ISO 27001 Training",
            "EGI Training Infrastructure",
            "EGI Dynamic DNS"
        ]


    def parse_service_name(self, details):
        # Parse service name using regex.
        try:
            for match in re.finditer("\"service\"", details.strip(), re.IGNORECASE):
                end = match.end()
                _tmp = details[end+1:-1].split(",", 1)[0]
                # Remove quotes
                return _tmp[1:len(_tmp)-1]
        except Exception:
            return None
        return None

    def process_orders(self, orders):
        # Initialize buckets
        service_buckets = {s: [] for s in self.egi_services}
        
        for order in orders:
             # Check Issue Type
             if self.env.get('SERVICE_ORDERS_ISSUETYPE') not in order['fields']['issuetype']['name']:
                 continue
             
             # Extract Service Name
             details = order['fields'].get('customfield_10711', '')
             if not details:
                 continue
                 
             service_name = self.parse_service_name(details)
             if not service_name:
                 continue
             
             # Map orders to service buckets.
             mapped = False
             
             for target in self.egi_services:
                 if service_name.lower() in target.lower():
                     service_buckets[target].append(order['key'])
                     mapped = True
                     break
             
             # Handle special case for "Software Distribution" typo mapping.
             if not mapped:
                  service_lower = service_name.lower()
                  if "software distribution" in service_lower or "sofware distribution" in service_lower:
                      service_buckets["EGI Software Distribution"].append(order['key'])
                  elif "workload manager" in service_lower:
                       service_buckets["EGI Workload Manager"].append(order['key'])
                  elif "infrastructure manager" in service_lower:
                       service_buckets["EGI Infrastructure Manager"].append(order['key'])
                  elif "dynamic dns" in service_lower:
                       service_buckets["EGI Dynamic DNS"].append(order['key'])
                  # Add more mappings if needed.
        
        return service_buckets

    def get_column_by_label(self, worksheet, label):
        """Find column index by its header label. Returns None if not found."""
        try:
            cell = worksheet.find(label.strip())
            return cell.col if cell else None
        except:
            return None

    def get_service_position(self, worksheet, service_name):
        """Find the lexicographical row position for a new service."""
        all_values = worksheet.get_all_values()
        row = 2 # Starting row for data
        if len(all_values) > 1:
            for values in all_values[1:]: # Check from row 2
                existing_service = values[0] if values else ""
                if existing_service < service_name:
                    row += 1
                else:
                    break
        return row

    def update_headers(self, worksheet, reporting_period):
        """Ensure base headers and period column exist."""
        headers = worksheet.row_values(1)
        if not headers:
            headers = ["Service"]
            worksheet.update('A1', [["Service"]])
        elif "Service" not in headers:
            worksheet.insert_cols([["Service"]], 1, value_input_option='RAW')
            headers = worksheet.row_values(1)

        # Ensure period column exists
        period_col = self.get_column_by_label(worksheet, reporting_period)
        if period_col:
            return period_col

        # find where to insert
        period_col = 2
        if headers:
            for h in headers:
                if h and h != "Service" and h < reporting_period:
                    period_col += 1
                else:
                    break
        
        print(f"Adding period {reporting_period} at column {period_col}")
        worksheet.insert_cols([[reporting_period]], period_col, inherit_from_before=True)
        return period_col

    def update_sheet_orders(self, worksheet, reporting_period, buckets):
        # Format
        worksheet.format("A1:P1", {
            "backgroundColor": {"red": 55.0, "green": 15.0, "blue": 10.0},
            "horizontalAlignment": "LEFT",
            "textFormat": {"fontSize": 11, "bold": True}
        })
        worksheet.format("A2:P300", {
            "horizontalAlignment": "RIGHT",
            "textFormat": {"fontSize": 10}
        })

        # Ensure headers exist
        period_col = self.update_headers(worksheet, reporting_period)

        # Get all services in column 1
        all_rows = worksheet.get_all_values()
        all_services = [r[0] if r else "" for r in all_rows]
        remaining_services = []
        cells_to_update = []

        # 1. Update Existing
        for service_name, so_list in buckets.items():
            try:
                row_index = None
                if service_name in all_services:
                    row_index = all_services.index(service_name) + 1
                
                if not row_index:
                    remaining_services.append(service_name)
                    continue
                
                so_string = ', '.join(so_list)
                cells_to_update.append(gspread.Cell(row_index, period_col, len(so_list)))
                
                try:
                    worksheet.insert_note(
                        gspread.utils.rowcol_to_a1(row_index, period_col),
                        so_string
                    )
                except:
                    pass

                if self.env.get('LOG') == "DEBUG":
                    print(f"Buffered update for {service_name}: {len(so_list)} orders")

            except Exception as e:
                if "Quota exceeded" in str(e):
                    time.sleep(60)
                    remaining_services.append(service_name)
                else:
                    remaining_services.append(service_name)
        
        # 2. Insert New
        if remaining_services:
            print(colourise("cyan", "\n[INFO]"), f"Adding {len(remaining_services)} new services (Batch Mode)...")
            # Sort for deterministic layout
            remaining_services.sort()
            
            # Determine start row for the batch
            # If sheet is empty (just headers), insert at row 2.
            start_row = self.get_service_position(worksheet, remaining_services[0])
            
            body = [[s] for s in remaining_services]
            try:
                worksheet.insert_rows(body, row=start_row, value_input_option='RAW')
                print(colourise("green", "[SUCCESS]"), f"Inserted {len(remaining_services)} services.")
                
                # Now buffer cell updates and notes for the new rows
                for i, service_name in enumerate(remaining_services):
                    current_row = start_row + i
                    so_list = buckets[service_name]
                    so_string = ', '.join(so_list)
                    
                    cells_to_update.append(gspread.Cell(current_row, period_col, len(so_list)))
                    try:
                        worksheet.insert_note(
                            gspread.utils.rowcol_to_a1(current_row, period_col),
                            so_string
                        )
                    except:
                        pass
            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Batch insertion failed: {e}")

        # 3. Perform batch update
        if cells_to_update:
            print(colourise("cyan", "[INFO]"), f"Performing batch update of {len(cells_to_update)} cells...")
            try:
                worksheet.update_cells(cells_to_update, value_input_option='RAW')
            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Failed batch update: {e}")

    def run(self, dry_run=False):
        print(f"\nLog Level = {colourise('cyan', self.env.get('LOG', 'INFO'))}")
        
        reporting_period = format_reporting_period(self.env)
        print(colourise("cyan", "\n[INFO]"), f"Reporting Period: '{reporting_period}'")

        if reporting_period in ["UNKNOWN_PERIOD", "INVALID_PERIOD"]:
            print(colourise("red", "[ABORT]"), "Cannot proceed with invalid or unknown reporting period.")
            return

        # Initialize the Google Worksheet.
        worksheet = init_GWorkSheet(self.env, 'GOOGLE_ORDERS_WORKSHEET')
        
        if not worksheet and not dry_run:
            return

        
        try:
            orders = get_service_orders(self.env)
        except KeyError as e:
            if dry_run:
                print(colourise("yellow", f"[DRY-RUN] Skipping Jira fetch due to missing config: {e}"))
                orders = []
            else:
                raise e
        buckets = self.process_orders(orders)
        
        if self.env.get('LOG') == "DEBUG":
            print(json.dumps(buckets, indent=4))
            
        if dry_run:
            print(colourise("yellow", "\n[DRY-RUN]"), f"Processed {len(orders)} orders into service buckets.")
            print("Service Order Counts:")
            for service, keys in buckets.items():
                if keys:
                    print(f" - {service}: {len(keys)}")
        else:
            self.update_sheet_orders(worksheet, reporting_period, buckets)

if __name__ == "__main__":
    app = OrdersAccounting()
    app.run()
