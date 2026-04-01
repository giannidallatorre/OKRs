
import unittest
from unittest.mock import MagicMock, patch
from egi_okr.base_accounting import BaseAccounting

class TestBaseAccounting(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
        }
        self.app = BaseAccounting(self.env)

    def test_get_period_column_descending(self):
        mock_ws = MagicMock()
        
        # Scenario 1: Empty headers, should insert at start_col (default 2)
        mock_ws.row_values.return_value = ['Labels']
        self.app.accounting_period = '2024.01-03'
        col = self.app.get_period_column(mock_ws, start_col=2)
        self.assertEqual(col, 2)
        mock_ws.insert_cols.assert_called_with([['2024.01-03']], 2, value_input_option='RAW', inherit_from_before=True)
        
        # Scenario 2: Existing older period, new period should go to the left (column 2)
        mock_ws.row_values.return_value = ['Labels', '2023.10-12']
        mock_ws.insert_cols.reset_mock()
        col = self.app.get_period_column(mock_ws, start_col=2)
        self.assertEqual(col, 2)
        mock_ws.insert_cols.assert_called_with([['2024.01-03']], 2, value_input_option='RAW', inherit_from_before=True)

        # Scenario 3: Existing newer period, new period should go to the right
        mock_ws.row_values.return_value = ['Labels', '2024.04-06']
        mock_ws.insert_cols.reset_mock()
        col = self.app.get_period_column(mock_ws, start_col=2)
        self.assertEqual(col, 3)
        mock_ws.insert_cols.assert_called_with([['2024.01-03']], 3, value_input_option='RAW', inherit_from_before=True)

        # Scenario 4: Multiple periods, insert in the middle
        mock_ws.row_values.return_value = ['Labels', '2024.04-06', '2023.10-12']
        mock_ws.insert_cols.reset_mock()
        col = self.app.get_period_column(mock_ws, start_col=2)
        self.assertEqual(col, 3)
        mock_ws.insert_cols.assert_called_with([['2024.01-03']], 3, value_input_option='RAW', inherit_from_before=True)

    def test_get_item_row_descending(self):
        mock_ws = MagicMock()
        all_values = [
            ['Labels'],
            ['2024.04-06'],
            ['2023.10-12']
        ]
        
        # Case 1: Newest period (at the top)
        row = self.app.get_item_row(mock_ws, '2024.07-09', start_row=2, all_values=all_values, descending=True)
        self.assertEqual(row, 2)
        
        # Case 2: Oldest period (at the bottom)
        row = self.app.get_item_row(mock_ws, '2023.07-09', start_row=2, all_values=all_values, descending=True)
        self.assertEqual(row, 4)
        
        # Case 3: Middle period
        row = self.app.get_item_row(mock_ws, '2024.01-03', start_row=2, all_values=all_values, descending=True)
        self.assertEqual(row, 3)

if __name__ == '__main__':
    unittest.main()
