import requests
import datetime
import gspread
from .utils import get_env_settings, handle_exception, init_GWorkSheet, format_reporting_period, colourise

class BaseAccounting:
    """Base class for all accounting modules to centralize GSpread logic and boilerplate."""
    
    def __init__(self, env=None):
        self.env = env if env is not None else get_env_settings()
        self.accounting_period = format_reporting_period(self.env)
        self.log_level = self.env.get('LOG', 'INFO')
        
        # Connection reuse: use provided session (for backfills) or create new one
        self.session = self.env.get('_requests_session')
        if not self.session:
            self.session = requests.Session()

    def init_worksheet(self, worksheet_env_key):
        """Initialize and return a GWorkSheet, or None on failure."""
        if self.accounting_period in ["UNKNOWN_PERIOD", "INVALID_PERIOD"]:
            return None
            
        return init_GWorkSheet(self.env, worksheet_env_key)

    def get_column_by_label(self, worksheet, label, headers=None):
        """Find column index by its header label. Returns None if not found."""
        if headers is None:
            try:
                headers = worksheet.row_values(1)
            except: return None
            
        if label in headers:
            return headers.index(label) + 1
        return None

    def get_period_column(self, worksheet, start_col=2, static_headers=None, headers=None):
        """Standardized logic to find or add the reporting period column in Row 1."""
        if headers is None:
            headers = worksheet.row_values(1)
        
        # 1. Existing?
        if self.accounting_period in headers:
            return headers.index(self.accounting_period) + 1

        # 2. Find insertion point
        y_pos = start_col
        if headers:
            for i, header in enumerate(headers):
                if i < (start_col - 1): continue
                if static_headers and header in static_headers: break
                if header == "" or header == "TOTAL": break
                if header < self.accounting_period:
                    y_pos = i + 2
                else:
                    y_pos = i + 1
                    break
        
        print(f"\tAdding period '{self.accounting_period}' at column {y_pos}")
        worksheet.insert_cols([[self.accounting_period]], y_pos, value_input_option='RAW', inherit_from_before=True)
        return y_pos

    def get_item_row(self, worksheet, item_name, start_row=2, first_col_index=1, all_values=None):
        """Lexicographical row finding for items in Column A (or first_col_index)."""
        if all_values is None:
            all_values = worksheet.get_all_values()
        
        row = start_row
        
        if len(all_values) >= start_row:
            for values in all_values[start_row-1:]:
                val = values[first_col_index-1] if len(values) >= first_col_index else ""
                if "TOTAL" in val.upper(): break
                if val < item_name:
                    row += 1
                else:
                    break
        return row

    def apply_standard_formatting(self, worksheet, last_col_letter='Z'):
        """Global aesthetic standardization."""
        worksheet.format(f"A1:{last_col_letter}1", {
            "backgroundColor": {"red": 55.0, "green": 15.0, "blue": 10.0},
            "horizontalAlignment": "LEFT",
            "textFormat": {"fontSize": 11, "bold": True}
        })
        worksheet.format(f"A2:{last_col_letter}500", {
            "horizontalAlignment": "RIGHT",
            "textFormat": {"fontSize": 10}
        })

    def update_timestamp(self, worksheet, cell="A1", prefix="Last update on: "):
        """Update last update note/cell."""
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        try:
            worksheet.insert_note(cell, f"{prefix}{timestamp}")
        except:
            pass

    def run(self, dry_run=False):
        """Common run loop wrapper."""
        raise NotImplementedError("Subclasses must implement run()")
