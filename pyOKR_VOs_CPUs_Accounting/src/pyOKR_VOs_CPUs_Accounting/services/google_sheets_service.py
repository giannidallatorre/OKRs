import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import GSpreadException
import datetime
import logging
from pyOKR_VOs_CPUs_Accounting.utils.utils import find_difference, handle_exception

class GoogleSheetsService:
    def __init__(self, env):
        self.env = env

    def init_GWorkSheet(self):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.env['SERVICE_ACCOUNT_FILE'], scope)
            client = gspread.authorize(creds)
            sheet = client.open(self.env['GOOGLE_SHEET_NAME']).worksheet(self.env['GOOGLE_HTC_WORKSHEET'])
            return sheet
        except KeyError as e:
            handle_exception(e, self.env)
        except FileNotFoundError as e:
            handle_exception(e, self.env)
        except GSpreadException as e:
            handle_exception(e, self.env)
        except Exception as e:
            handle_exception(e, self.env)

    def update_GWorkSheet(self, worksheet, accounting_period, summary):
        ''' Update the accounting records in the Google Worksheet '''
        try:
            worksheet_dicts = worksheet.get_all_records()
            # Formatting the header of the worksheet
            self.format_worksheet_header(worksheet)

            # Formatting the cells of the worksheet
            self.format_worksheet_cells(worksheet)

            timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            
            # Distinguish between None (invalid) and empty list (no VOs)
            if summary.get("VOs_complete_list") is None:
                raise ValueError("VOs_complete_list is None")

            # Build strings, use '-' when lists are empty
            if summary.get("VOs_complete_list"):
                VOs_string = ', '.join([str(elem.get('VO name')) for elem in summary["VOs_complete_list"]])
            else:
                VOs_string = '-'

            if summary.get("noVOsCPUs"):
                NOVOs_string = ', '.join([str(item) for item in summary["noVOsCPUs"]])
            else:
                NOVOs_string = '-'

            flag = False
            for item in worksheet_dicts:
                if item['Period'] == accounting_period:
                    cell = worksheet.find(item['Period'])
                    flag = True

                    # Updating the cell of the Google Worksheet
                    self.update_worksheet_cells(worksheet, cell, summary, VOs_string, NOVOs_string)

                    logging.info(f"Updated the Total {'Cloud' if self.env['ACCOUNTING_SCOPE'] == 'cloud' else 'HTC'} CPU/h for the reporting period: {accounting_period}")

            if not flag:
                accounting_period_pos, found_position = self.get_GWorkSheetCellPosition(worksheet, accounting_period)
                logging.info(f"Adding {accounting_period} at row: {accounting_period_pos}")

                if accounting_period_pos > 2:
                    newVOs_str, leavingVOs_str = find_difference(
                        worksheet.cell(accounting_period_pos, 4).value,
                        worksheet.cell(accounting_period_pos - 1, 4).value
                    )
                    result = f"APPEARED: {newVOs_str}\nDISAPPEARED: {leavingVOs_str}"
                    body = [accounting_period, summary["total_cloud_cpu_hours"], summary["total"], VOs_string, len(summary["noVOsCPUs"]), NOVOs_string, result]
                else:
                    body = [accounting_period, summary["total_cloud_cpu_hours"], summary["total"], VOs_string, len(summary["noVOsCPUs"]), NOVOs_string, '-']

                worksheet.insert_row(body, index=accounting_period_pos, inherit_from_before=True)

            worksheet.insert_note("A1", f"Last update on: {timestamp}")

        except (GSpreadException, ValueError) as e:
            handle_exception(e, self.env, worksheet)

    def format_worksheet_header(self, worksheet):
        worksheet.format("A1:H1", {
            "backgroundColor": {"red": 55.0, "green": 15.0, "blue": 10.0},
            "horizontalAlignment": "LEFT",
            "textFormat": {"fontSize": 11, "bold": True}
        })

    def format_worksheet_cells(self, worksheet):
        worksheet.format("A2:H100", {
            "horizontalAlignment": "RIGHT",
            "textFormat": {"fontSize": 11}
        })

    def update_worksheet_cells(self, worksheet, cell, summary, VOs_string, NOVOs_string):
        worksheet.update_cell(cell.row, cell.col + 1, summary["total_cloud_cpu_hours"])
        worksheet.update_cell(cell.row, cell.col + 2, summary["total"])
        worksheet.update_cell(cell.row, cell.col + 3, VOs_string if VOs_string else '-')
        worksheet.update_cell(cell.row, cell.col + 4, len(summary["noVOsCPUs"]))
        worksheet.update_cell(cell.row, cell.col + 5, NOVOs_string if len(summary["noVOsCPUs"]) else '-')

        if cell.row > 2:
            newVOs_str, leavingVOs_str = find_difference(
                worksheet.cell(cell.row - 1, 4).value,
                worksheet.cell(cell.row, 4).value
            )
            result = f"APPEARED: {newVOs_str}\nDISAPPEARED: {leavingVOs_str}"
            worksheet.update_cell(cell.row, cell.col + 6, result)
        else:
            worksheet.update_cell(cell.row, cell.col + 6, '-')

    def get_GWorkSheetCellPosition(self, worksheet, accounting_period):
        ''' Get the cell coordinates where to add the new reporting period '''
        found = False
        pos = 2

        values_list = worksheet.col_values(1)

        if len(values_list) > 1:
            for header in values_list:
                if ("Period" not in header):
                    if (header == accounting_period) or (header == ""):
                        found = True
                        break
                    if header < accounting_period:
                        pos = pos + 1

        return(pos, found)