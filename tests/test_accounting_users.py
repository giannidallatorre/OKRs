
import unittest
import datetime
from unittest.mock import patch, MagicMock
from egi_okr.accounting_users import UsersAccounting

class TestUsersAccounting(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'LOG': 'DEBUG',
            'GOOGLE_SHEET_NAME': 'dummy',
            'GOOGLE_VOS_WORKSHEET': 'VOs',
            'GOOGLE_VOS_REPORT_WORKSHEET': 'Reports',
            'OPERATIONS_SERVER_URL': 'http://ops',
            'OPERATIONS_API_KEY': 'key'
        }
        self.app = UsersAccounting(self.env)

    @patch('egi_okr.accounting_users.get_VOs_stats')
    @patch('egi_okr.accounting_users.get_VOs_report')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_run_flow(self, mock_init, mock_get_report, mock_get_stats):
        # Mock Sheets
        mock_ws_vos = MagicMock()
        mock_ws_reports = MagicMock()
        mock_init.side_effect = [mock_ws_vos, mock_ws_reports]
        
        # Mock Stats
        mock_get_stats.return_value = [{'name': 'vo.test', 'users': 10, 'active_members': 5, 'total_members': 100}]
        mock_get_report.return_value = []
        
        # Mock values for BaseAccounting logic
        mock_ws_vos.row_values.return_value = ['VO', 'Registered Users', 'Total Users']
        mock_ws_vos.get_all_values.return_value = [['VO', 'Registered Users', 'Total Users']]
        mock_ws_reports.get_all_values.return_value = [['Period', 'Count']]
        
        self.app.run()
        
        # Verify batch update in process_vos
        mock_ws_vos.update_cells.assert_called()

if __name__ == '__main__':
    unittest.main()
