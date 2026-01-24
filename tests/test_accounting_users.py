
import unittest
from unittest.mock import patch, MagicMock
from egi_okr.accounting_users import UsersAccounting

class TestUsersAccounting(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'LOG': 'DEBUG',
            'GOOGLE_VOS_WORKSHEET': 'VOs',
            'SERVICE_ACCOUNT_FILE': 'dummy.json',
            'GOOGLE_SHEET_NAME': 'dummy_sheet'
        }
        self.app = UsersAccounting(self.env)
        self.app.env['OPERATIONS_API_KEY'] = 'key'
        self.app.env['OPERATIONS_SERVER_URL'] = 'url'
        self.app.env['OPERATIONS_FORMAT'] = 'json'

    @patch('egi_okr.accounting_users.init_GWorkSheet')
    @patch('egi_okr.accounting_users.get_VOs_stats')
    def test_run_flow(self, mock_get_stats, mock_init_sheet):
        # Mock Sheet
        mock_worksheet = MagicMock()
        mock_init_sheet.return_value = mock_worksheet
        
        # Mock existing data
        mock_worksheet.get_all_records.return_value = [
            {'VO': 'ALICE', '2023.10-12': 10, 'Registered Users': 100, 'Total Users': 200},
            {'VO': 'ATLAS', '2023.10-12': 20, 'Registered Users': 300, 'Total Users': 400}
        ]
        mock_worksheet.row_values.return_value = ['VO', '2023.10-12', 'Registered Users', 'Total Users']
        
        # Mock find return values (Columns)
        # Using side_effect to return mocks with specific .col and .row attributes
        find_calls = []
        def find_side_effect(arg):
            if arg == '2024.01-03':
                if arg not in find_calls:
                    find_calls.append(arg)
                    return None # First call: not found
                # Subsequent calls: found
                m = MagicMock()
                m.col = 3
                return m
            
            m = MagicMock()
            if arg == 'Registered Users':
                m.col = 4
            elif arg == 'Total Users':
                m.col = 5
            elif arg == 'ALICE': # VO cell
                m.row = 2
                m.col = 1
            else:
                 return None
            return m
            
        mock_worksheet.find.side_effect = find_side_effect

        def findall_side_effect(arg):
             if arg == 'ALICE':
                 m = MagicMock()
                 m.row = 2
                 m.col = 1
                 return [m]
             return []
        
        mock_worksheet.findall.side_effect = findall_side_effect


        # Mock Stats Data
        mock_get_stats.return_value = [
            {'name': 'ALICE', 'users': 15, 'active_members': 110, 'total_members': 210},
            {'name': 'CMS', 'users': 5, 'active_members': 50, 'total_members': 60}
        ]

        # Run
        self.app.run()
        
        # Assertions
        # 1. Headers updated?
        # accounting_period = '2024.01-03' (from env)
        # In mock data, '2023.10-12' is present. '2024.01-03' is larger.
        # It should call insert_cols.
        mock_worksheet.insert_cols.assert_called()
        
        # 2. Existing VO updated?
        # ALICE update should happen.
        # We check for batch update called with gspread.Cell objects.
        mock_worksheet.update_cells.assert_called()
        
        # 3. New VO inserted?
        # CMS is new. Should call insert_row.
        mock_worksheet.insert_row.assert_called()

if __name__ == '__main__':
    unittest.main()
