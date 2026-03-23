import os
import requests
import datetime
import gspread
from .utils import get_env_settings, handle_exception, init_GWorkSheet, format_reporting_period, colourise, gspread_retry

class BaseAccounting:
    """Base class for all accounting modules to centralize GSpread logic and boilerplate."""
    
    def __init__(self, env=None):
        self.env = env if env is not None else get_env_settings()
        self.accounting_period = format_reporting_period(self.env)
        self.log_level = self.env.get('LOG', 'INFO')
        self.print_mode = self.env.get('PRINT_MODE', 'False') == 'True'
        
        # Connection reuse: use provided session (for backfills) or create new one
        self.session = self.env.get('_requests_session')
        if not self.session:
            self.session = requests.Session()
            # Increase pool size for parallel requests (default is 10)
            adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)
            
        # Proactive Auto-Print Fallback:
        # If not in print_mode, check if we actually HAVE credentials.
        # If not, switch to print_mode automatically to avoid cryptic [ABORT] errors.
        if not self.print_mode:
            has_creds = ('SERVICE_ACCOUNT_JSON' in self.env) or \
                        ('SERVICE_ACCOUNT_FILE' in self.env and os.path.exists(self.env['SERVICE_ACCOUNT_FILE']))
            has_sheet = bool(self.env.get('GOOGLE_SHEET_NAME'))
            
            if not has_creds or not has_sheet:
                self.print_mode = True
                print(colourise("cyan", "[INFO]"), "Google Sheet credentials or Sheet Name missing.")
                print(colourise("cyan", "[INFO]"), "Switching to " + colourise("bold", "Auto-Print mode") + " (terminal output only).\n")

    @gspread_retry
    def init_worksheet(self, worksheet_env_key):
        """Initialize and return a GWorkSheet, or None on failure/print mode."""
        if self.print_mode:
            return None
            
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

    @gspread_retry
    def get_period_column(self, worksheet, start_col=2, static_headers=None, headers=None):
        """Standardized logic to find or add the reporting period column in Row 1.
        Default: Descending lexicographical order (newest first).
        """
        if headers is None:
            headers = worksheet.row_values(1)
        
        # 1. Existing?
        if self.accounting_period in headers:
            return headers.index(self.accounting_period) + 1

        # 2. Find insertion point (Descending: newest in column 2)
        y_pos = start_col
        if headers:
            for i, header in enumerate(headers):
                if i < (start_col - 1): continue
                if static_headers and header in static_headers: break
                if header == "" or header == "TOTAL": break
                
                # Descending logic: if current header is smaller than new period, insert here
                if header < self.accounting_period:
                    y_pos = i + 1
                    break
                else:
                    y_pos = i + 2
        
        print(f"\tAdding period '{self.accounting_period}' at column {y_pos}")
        worksheet.insert_cols([[self.accounting_period]], y_pos, value_input_option='RAW', inherit_from_before=True)
        return y_pos

    def get_item_row(self, worksheet, item_name, start_row=2, first_col_index=1, all_values=None, descending=False):
        """Lexicographical row finding for items in Column A (or first_col_index)."""
        if all_values is None:
            all_values = worksheet.get_all_values()
        
        row = start_row
        
        if len(all_values) >= start_row:
            for values in all_values[start_row-1:]:
                val = values[first_col_index-1] if len(values) >= first_col_index else ""
                if "TOTAL" in val.upper(): break
                
                if descending:
                    if val < item_name:
                        break
                    else:
                        row += 1
                else:
                    if val < item_name:
                        row += 1
                    else:
                        break
        return row

    @gspread_retry
    def apply_standard_formatting(self, worksheet, last_col_letter='Z'):
        """Apply consistent formatting style to all sheets."""
        worksheet.batch_format([
            {
                'range': f'A1:{last_col_letter}1',
                'format': {
                    "backgroundColor": {"red": 55.0, "green": 15.0, "blue": 10.0},
                    "horizontalAlignment": "LEFT",
                    "textFormat": {"fontSize": 11, "bold": True}
                }
            },
            {
                'range': f'A2:{last_col_letter}500',
                'format': {
                    "horizontalAlignment": "RIGHT",
                    "textFormat": {"fontSize": 10}
                }
            }
        ])

    @gspread_retry
    def update_timestamp(self, worksheet, cell="A1", prefix="Last update on: "):
        """Update last update note/cell."""
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        try:
            worksheet.insert_note(cell, f"{prefix}{timestamp}")
        except:
            pass

    @gspread_retry
    def update_worksheet_data(self, worksheet, row_labels, data_map, first_col_label="Metric", start_row=2, period_col=None):
        """
        Centralized 'Read-Once, Write-Batch' logic for per-worksheet updates.
        
        Args:
            worksheet: GSpread worksheet object.
            row_labels: List of strings for Column A labels (if they need initialization).
            data_map: Dict of {label: value} to write to the period column.
            first_col_label: Header for Column A.
            start_row: Row where data begins.
            period_col: Optional pre-calculated period column index.
            
        Returns:
            int: The period column index used.
        """
        if not worksheet:
            return None

        # 1. READ ONCE
        all_values = worksheet.get_all_values()
        headers = all_values[0] if all_values else []
        existing_labels = [r[0] if r else "" for r in all_values]

        # 2. Initialize Headers/Labels if needed
        if not headers or (first_col_label and first_col_label not in headers[0]):
            print(f"\tInitializing worksheet headers for '{worksheet.title}'...")
            worksheet.update('A1', [[first_col_label]], value_input_option='RAW')
            if row_labels:
                worksheet.update(f'A{start_row}:A{start_row + len(row_labels) - 1}', 
                                [[l] for l in row_labels], value_input_option='RAW')
            # Local update to avoid re-reading all values (Save 1 API call per initialized sheet)
            headers = [first_col_label]
            existing_labels = [first_col_label] + row_labels

        # 3. Apply standard formatting (Singleton-ish: once per run)
        self.apply_standard_formatting(worksheet)

        # 4. Find or Create Period Column
        if period_col is None:
            period_col = self.get_period_column(worksheet, headers=headers)

        # 5. Prepare Batch Updates
        cells_to_update = []
        
        # Track if we need to insert any NEW rows (labels not in existing_labels)
        new_items = []
        for label, value in data_map.items():
            if label in existing_labels:
                row_idx = existing_labels.index(label) + 1
                cells_to_update.append(gspread.Cell(row_idx, period_col, value))
            else:
                new_items.append((label, value))

        # 6. Handle New Items (Insert and Sort)
        if new_items:
            new_items.sort(key=lambda x: x[0])
            for label, value in new_items:
                # Find insertion row
                row_idx = self.get_item_row(worksheet, label, start_row=start_row, all_values=all_values)
                print(f"\tInserting new label '{label}' at row {row_idx}")
                worksheet.insert_row([label], index=row_idx)
                # We must update local existing_labels to track indices for subsequent cells in this batch
                existing_labels.insert(row_idx - 1, label)
                # Re-calculate all_values if we wanted to be perfectly accurate for subsequent insertions,
                # but for simplicity we rely on index tracking.
                cells_to_update.append(gspread.Cell(row_idx, period_col, value))

        # 7. WRITE BATCH
        if cells_to_update:
            print(f"\tPerforming batch update of {len(cells_to_update)} cells in '{worksheet.title}'...")
            worksheet.update_cells(cells_to_update, value_input_option='RAW')
            self.update_timestamp(worksheet)

        # 8. Defensive Delay (Per-Worksheet)
        import time
        write_delay = int(self.env.get('WRITE_DELAY', 1))
        if write_delay > 0:
            time.sleep(write_delay)

        return period_col

    def run(self, dry_run=False):
        """Common run loop wrapper."""
        raise NotImplementedError("Subclasses must implement run()")
