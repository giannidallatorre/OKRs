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

    def get_header_position(self, worksheet, reporting_period):
        headers_list = worksheet.row_values(1)
        col = 2
        for header in headers_list:
            if "Services" not in header:
                if header != reporting_period:
                    col += 1
                else:
                    break
        return col

    def get_service_position(self, worksheet, service):
        row = 3
        worksheet_dicts = worksheet.get_all_records()
        for item in worksheet_dicts:
            if "TOTAL" not in item.get('Services', ''):
                if item.get('Services', '') <= service:
                    row += 1
                else:
                    break
        return row

    def update_headers(self, worksheet, reporting_period):
        y_pos = 2
        flag = True
        
        worksheet_dicts = worksheet.get_all_records()
        if worksheet_dicts:
            for header in worksheet_dicts[0]:
                if "Services" not in header:
                    if header == reporting_period:
                        y_pos = -1
                        break
                    if header < reporting_period:
                        y_pos += 1
                    else:
                        break
                        
            if y_pos >= 2 or y_pos > len(worksheet_dicts[0]):
                flag = False

        if not flag and y_pos > 0:
            print(f"Adding '{reporting_period}' at column: {y_pos}")
            worksheet.insert_cols(
                [[reporting_period]], 
                y_pos, 
                value_input_option='RAW', 
                inherit_from_before=True
            )
        else:
            print(f"The header '{reporting_period}' is *already* in the Worksheet")

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
        
        # Update Existing services in the sheet.
        try:
             # Find period column
             found_period = worksheet.findall(reporting_period)
             period_col = None
             for c in found_period:
                  if c.row == 1: # Header row
                       period_col = c.col
                       break
             if not period_col:
                  raise Exception("Period not found")
        except:
             print(colourise("red", "[ERROR]"), f"Period {reporting_period} not found in header")
             return

        remaining_services = []

        for service_name, so_list in buckets.items():
            if not so_list and len(buckets[service_name]) == 0:
                pass
            
            try:
                # Find service row
                found_cells = worksheet.findall(service_name)
                cell = None
                for c in found_cells:
                    if c.col == 1:
                        cell = c
                        break
                
                if not cell:
                    remaining_services.append(service_name)
                    continue
                
                # Update
                so_string = ', '.join(so_list)
                worksheet.update_cell(cell.row, period_col, len(so_list))
                worksheet.insert_note(
                    gspread.utils.rowcol_to_a1(cell.row, period_col),
                    so_string
                )
                print(f"Updated {service_name}: {len(so_list)} orders")

            except Exception as e:
                # Handle quota
                 if "Quota exceeded" in str(e):
                      time.sleep(60)
                      remaining_services.append(service_name)
                 else:
                      # If not found (shouldn't happen with findall logic above), append
                      remaining_services.append(service_name)
        
        # 2. Insert New
        if remaining_services:
            print(colourise("cyan", "\n[INFO]"), "Adding new services...")
            col_index = self.get_header_position(worksheet, reporting_period)
            
            for service_name in remaining_services:
                so_list = buckets[service_name]
                
                try:
                    row_index = self.get_service_position(worksheet, service_name)
                    print(f"Insert {service_name} at row {row_index}")
                    
                    worksheet.insert_row(['', ''], index=row_index)
                    worksheet.update_cell(row_index, 1, service_name)
                    
                    worksheet.update_cell(row_index, col_index, len(so_list))
                    
                    so_string = ', '.join(so_list)
                    worksheet.insert_note(
                        gspread.utils.rowcol_to_a1(row_index, col_index),
                        so_string
                    )
                except Exception as e:
                    print(colourise("red", "[ERROR]"), f"Failed to insert {service_name}: {e}")

    def run(self):
        print(f"\nLog Level = {colourise('cyan', self.env.get('LOG', 'INFO'))}")
        
        reporting_period = format_reporting_period(self.env)
        print(colourise("cyan", "\n[INFO]"), f"Reporting Period: '{reporting_period}'")

        if reporting_period in ["UNKNOWN_PERIOD", "INVALID_PERIOD"]:
            print(colourise("red", "[ABORT]"), "Cannot proceed with invalid or unknown reporting period.")
            return

        # Initialize the Google Worksheet.
        worksheet = init_GWorkSheet(self.env, 'GOOGLE_ORDERS_WORKSHEET')
        
        if not worksheet:
            return

        self.update_headers(worksheet, reporting_period)
        
        orders = get_service_orders(self.env)
        buckets = self.process_orders(orders)
        
        if self.env.get('LOG') == "DEBUG":
            print(json.dumps(buckets, indent=4))
            
        self.update_sheet_orders(worksheet, reporting_period, buckets)

if __name__ == "__main__":
    app = OrdersAccounting()
    app.run()
