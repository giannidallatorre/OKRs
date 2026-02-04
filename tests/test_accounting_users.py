
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
            'GOOGLE_VOS_REPORT_WORKSHEET': 'Report',
            'GOOGLE_SHEET_NAME': 'dummy'
        }
        self.app = UsersAccounting(self.env)

    @patch('egi_okr.base_accounting.init_GWorkSheet')
    @patch('egi_okr.accounting_users.get_VOs_stats')
    @patch('egi_okr.accounting_users.get_VOs_report')
    def test_run_flow(self, mock_get_report, mock_get_stats, mock_init_sheet):
        # 1. Mock Sheets
        mock_worksheet = MagicMock()
        mock_report_ws = MagicMock()
        mock_init_sheet.side_effect = [mock_worksheet, mock_report_ws]
        
        # 2. Mock Data
        mock_get_stats.return_value = [{'name': 'ALICE', 'users': 15, 'active_members': 110, 'total_members': 210}]
        mock_get_report.return_value = [{'status': 'Production', 'count': 1, 'vos': ['ALICE']}]
        
        # Mock main sheet headers
        mock_worksheet.row_values.return_value = ['VO', '2023.10-12', 'Registered Users', 'Total Users']
        mock_worksheet.get_all_values.return_value = [['VO', '2023.10-12', 'Registered Users', 'Total Users'], ['ALICE', '10', '100', '200']]
        
        # Mock report sheet finding
        mock_report_ws.findall.return_value = []
        
        # Run
        self.app.run()
        
        # Verify
        mock_worksheet.update_cells.assert_called()
        mock_report_ws.insert_row.assert_called()

if __name__ == '__main__':
    unittest.main()
