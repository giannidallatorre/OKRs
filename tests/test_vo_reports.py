
import unittest
from unittest.mock import patch, MagicMock
from egi_okr.vo_reports import VOsReports

class TestVOsReports(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'LOG': 'DEBUG',
            'GOOGLE_SHEET_NAME': 'dummy',
            'GOOGLE_VOS_REPORT_WORKSHEET': 'Report',
            'OPERATIONS_API_KEY': 'key',
            'OPERATIONS_SERVER_URL': 'url'
        }
        self.app = VOsReports(self.env)

    @patch('egi_okr.vo_reports.init_GWorkSheet')
    @patch('egi_okr.vo_reports.get_VOs_report')
    def test_run_flow_insert(self, mock_get_report, mock_init_sheet):
        mock_worksheet = MagicMock()
        mock_init_sheet.return_value = mock_worksheet
        
        # Mock get_VOs_report return
        mock_get_report.return_value = [
            {'status': 'Production', 'count': 5, 'vos': ['A', 'B', 'C', 'D', 'E']},
            {'status': 'Deleted', 'count': 2, 'vos': ['X', 'Y']}
        ]
        
        # Mock findall (reporting period not found -> empty)
        mock_worksheet.findall.return_value = []
        
        # Mock col_values for get_cell_position
        # Existing headers: Period, older_period
        mock_worksheet.col_values.return_value = ['Period', '2023.10-12']
        
        self.app.run()
        
        # Expectation:
        # Total = 5 + 2 = 7
        # Deleted = 2
        # Production = 5
        # Insert row called.
        mock_worksheet.insert_row.assert_called()
        args, _ = mock_worksheet.insert_row.call_args
        body = args[0]
        # Body: [period, total, deleted, production, string]
        self.assertEqual(body[1], 7)
        self.assertEqual(body[2], 2)
        self.assertEqual(body[3], 5)

    @patch('egi_okr.vo_reports.init_GWorkSheet')
    @patch('egi_okr.vo_reports.get_VOs_report')
    def test_run_flow_update(self, mock_get_report, mock_init_sheet):
        mock_worksheet = MagicMock()
        mock_init_sheet.return_value = mock_worksheet
        
        mock_get_report.return_value = [{'status': 'Production', 'count': 1, 'vos': ['Z']}]
        
        # Mock findall (period found)
        m = MagicMock()
        m.col = 1
        m.row = 5
        mock_worksheet.findall.return_value = [m]
        
        self.app.run()
        
        # Expectation: update_cells called (batch update instead of individual update_cell)
        mock_worksheet.update_cells.assert_called()
        # Verify it was called with a list of cells
        args, kwargs = mock_worksheet.update_cells.call_args
        cells = args[0]
        self.assertEqual(len(cells), 4)  # 4 cells updated (total, deleted, production, vos_string)

if __name__ == '__main__':
    unittest.main()
