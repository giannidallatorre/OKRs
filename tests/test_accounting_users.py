
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
            'GOOGLE_VOS_REGISTERED_WORKSHEET': 'VOs-Registered',
            'GOOGLE_VOS_TOTAL_WORKSHEET': 'VOs-Total',
            'GOOGLE_VOS_REPORT_WORKSHEET': 'Reports',
            'OPERATIONS_SERVER_URL': 'http://ops',
            'OPERATIONS_API_KEY': 'key',
            'GOOGLE_SHEET_NAME': 'dummy',
            'SERVICE_ACCOUNT_JSON': '{"client_email": "test@test.com", "private_key": "-----BEGIN PRIVATE KEY-----\\nFAKE\\n-----END PRIVATE KEY-----"}'
        }
        self.app = UsersAccounting(self.env)

    @patch('egi_okr.accounting_users.get_VOs_stats')
    @patch('egi_okr.accounting_users.get_VOs_report')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_run_flow(self, mock_init, mock_get_report, mock_get_stats):
        # Mock Sheets (now 4 sheets: active, registered, total, reports)
        mock_ws_active = MagicMock()
        mock_ws_registered = MagicMock()
        mock_ws_total = MagicMock()
        mock_ws_reports = MagicMock()
        mock_init.side_effect = [mock_ws_active, mock_ws_registered, mock_ws_total, mock_ws_reports]
        
        # Mock Stats
        mock_get_stats.return_value = [{'name': 'vo.test', 'users': 10, 'active_members': 5, 'total_members': 100}]
        mock_get_report.return_value = []
        
        # Mock values for BaseAccounting logic (simple headers for all sheets)
        mock_ws_active.row_values.return_value = ['VO']
        mock_ws_active.get_all_values.return_value = [['VO']]
        
        mock_ws_registered.row_values.return_value = ['VO']
        mock_ws_registered.get_all_values.return_value = [['VO']]
        
        mock_ws_total.row_values.return_value = ['VO']
        mock_ws_total.get_all_values.return_value = [['VO']]
        
        mock_ws_reports.get_all_values.return_value = [['Period', 'Count']]
        
        self.app.run()
        
        # Verify batch update in all three metric sheets
        mock_ws_active.update_cells.assert_called()
        mock_ws_registered.update_cells.assert_called()
        mock_ws_total.update_cells.assert_called()

    @patch('egi_okr.accounting_users.get_VOs_stats')
    @patch('egi_okr.accounting_users.get_VOs_report')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_users_data_not_empty_regression(self, mock_init, mock_get_report, mock_get_stats):
        """
        Regression test: Ensure all three user metric sheets report data.
        
        This catches bugs where header initialization or data refresh 
        prevents data from being written to the sheets.
        """
        # Mock all four worksheets
        mock_ws_active = MagicMock()
        mock_ws_registered = MagicMock()
        mock_ws_total = MagicMock()
        mock_ws_reports = MagicMock()
        mock_init.side_effect = [mock_ws_active, mock_ws_registered, mock_ws_total, mock_ws_reports]
        
        # Mock realistic data from Operations API
        mock_get_stats.return_value = [
            {'name': 'vo.alice', 'users': 15, 'active_members': 8, 'total_members': 120},
            {'name': 'vo.bob', 'users': 22, 'active_members': 12, 'total_members': 95},
        ]
        mock_get_report.return_value = [
            {'status': 'Created', 'count': 3, 'vos': 'vo.alpha,vo.beta,vo.gamma'},
        ]
        
        # Mock worksheet states - simulate needing header initialization
        call_count = {'active': 0, 'registered': 0, 'total': 0}
        
        def active_get_all_values():
            call_count['active'] += 1
            if call_count['active'] <= 1:
                return [[]]  # Empty, needs header init
            else:
                return [['VO', '2024.01-03'], ['vo.alice', 15], ['vo.bob', 22]]
        
        def registered_get_all_values():
            call_count['registered'] += 1
            if call_count['registered'] <= 1:
                return [[]]  # Empty, needs header init
            else:
                return [['VO', '2024.01-03'], ['vo.alice', 8], ['vo.bob', 12]]
        
        def total_get_all_values():
            call_count['total'] += 1
            if call_count['total'] <= 1:
                return [[]]  # Empty, needs header init
            else:
                return [['VO', '2024.01-03'], ['vo.alice', 120], ['vo.bob', 95]]
        
        mock_ws_active.get_all_values.side_effect = active_get_all_values
        mock_ws_active.cell.return_value.value = None
        
        mock_ws_registered.get_all_values.side_effect = registered_get_all_values
        mock_ws_registered.cell.return_value.value = None
        
        mock_ws_total.get_all_values.side_effect = total_get_all_values
        mock_ws_total.cell.return_value.value = None
        
        mock_ws_reports.get_all_values.return_value = [['Period', 'Total', 'Deleted', 'Production', 'VO List']]
        
        self.app.run()
        
        # REGRESSION CHECKS:
        # 1. All three metric sheets should have data written
        self.assertTrue(mock_ws_active.update_cells.called, 
                       "Active Users sheet should have data written")
        self.assertTrue(mock_ws_registered.update_cells.called,
                       "Registered Users sheet should have data written")
        self.assertTrue(mock_ws_total.update_cells.called,
                       "Total Users sheet should have data written")
        
        # 2. Each should have data for both VOs
        for sheet_name, mock_ws in [('active', mock_ws_active), 
                                     ('registered', mock_ws_registered),
                                     ('total', mock_ws_total)]:
            cells = mock_ws.update_cells.call_args[0][0]
            self.assertGreaterEqual(len(cells), 2, 
                                   f"{sheet_name} should have at least 2 VO entries")

if __name__ == '__main__':
    unittest.main()
