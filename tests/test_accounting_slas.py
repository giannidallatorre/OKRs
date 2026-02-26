
import unittest
import datetime
from unittest.mock import patch, MagicMock
from egi_okr.accounting_slas import SLAsAccounting

class TestSLAsAccounting(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'LOG': 'DEBUG',
            'GOOGLE_SLAs_WORKSHEET': 'SLAs',
            'GOOGLE_SLAs_CLOUD_WORKSHEET': 'SLA-Cloud',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_SERVER_URL': 'http://acc',
            'ACCOUNTING_METRIC': 'metric',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'local',
            'ACCOUNTING_DATA_SELECTOR': 'data',
            'ACCOUNTING_BENCHMARK_SELECTOR': 'hepspec06',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi'
        }
        self.app = SLAsAccounting(self.env)

    @patch('egi_okr.operations.get_VOs_stats')
    def test_fetch_active_slas(self, mock_get_vos):
        # Mock API response
        mock_get_vos.return_value = [{'name': 'vo.test'}]
        
        slas = self.app.fetch_active_slas()
        self.assertEqual(len(slas), 1)
        self.assertEqual(slas[0]['Name'], "vo.test")

    @patch('egi_okr.operations.get_VOs_stats')
    @patch('requests.Session.get')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_run_flow(self, mock_init, mock_get, mock_get_vos):
        # 1. Mock Sheets
        mock_target_ws = MagicMock()
        mock_init.return_value = mock_target_ws
        
        # 2. Mock API call to get VOs
        mock_get_vos.return_value = [{'name': 'vo.test'}]
        
        # 3. Mock Target Sheet (Results sheet)
        mock_target_ws.get_all_values.return_value = [['VO', '2024.01-03']]
        
        # 4. Mock API (Individual VO fetch via session)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{'id': 'Total', 'Total': 123}]
        mock_get.return_value = mock_resp
        
        self.app.run()
        
        # Verify batch update
        mock_target_ws.update_cells.assert_called()
        # Verify the cell value
        cells = mock_target_ws.update_cells.call_args[0][0]
        self.assertEqual(cells[0].value, 123)

    @patch('egi_okr.operations.get_VOs_stats')
    @patch('requests.Session.get')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_header_initialization_with_existing_data_regression(self, mock_init, mock_get, mock_get_vos):
        """
        Regression test: Verify that when headers are initialized, 
        existing VOs are correctly identified and updated (not re-inserted).
        
        This test catches the bug where all_rows and existing_names weren't 
        refreshed after header initialization, causing all VOs to be treated 
        as new inserts instead of updates, resulting in empty sheets.
        """
        # 1. Mock Sheets
        mock_target_ws = MagicMock()
        mock_init.return_value = mock_target_ws
        
        # 2. Mock API call to get VOs
        mock_get_vos.return_value = [{'name': 'vo.test'}]
        
        # 3. Mock Target Sheet - SIMULATE EMPTY HEADER (needs initialization)
        # First call returns empty sheet, simulating new sheet
        # get_all_values() is called multiple times:
        # - First in run() at line "all_rows = worksheet.get_all_values()"
        # - Second in setup after header init (should refresh)
        call_count = {'count': 0}
        def mock_get_all_values():
            call_count['count'] += 1
            if call_count['count'] == 1:
                # First call: sheet is empty (only needs header init)
                return [[]]
            else:
                # After header init: sheet has header + existing VO
                return [['VO', '2023.10-12'], ['vo.test', 456]]
        
        mock_target_ws.get_all_values.side_effect = mock_get_all_values
        mock_target_ws.cell.return_value.value = None  # Empty A1
        
        # 4. Mock API responses
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{'id': 'Total', 'Total': 789}]
        mock_get.return_value = mock_resp
        
        self.app.run()
        
        # CRITICAL ASSERTIONS:
        # 1. update() should be called for header initialization (via update_worksheet_data)
        self.assertTrue(mock_target_ws.update.called)
        # 2. update_cells should be called for data updates
        self.assertTrue(mock_target_ws.update_cells.called)
        
        # 3. Verify that at least one cell was updated (not all inserts)
        cells = mock_target_ws.update_cells.call_args[0][0]
        self.assertGreater(len(cells), 0, "Data should be written to cells")
        
        # 4. Verify that the value is the new CPU value (not empty/None)
        self.assertEqual(cells[0].value, 789, "CPU value should be updated with API data")

    @patch('egi_okr.operations.get_VOs_stats')
    @patch('requests.Session.get')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_slas_data_not_empty_regression(self, mock_init, mock_get, mock_get_vos):
        """
        Regression test: Ensure SLAs module always reports data when VOs exist.
        
        This catches the class of bugs where:
        - Data is fetched successfully (API calls work)
        - But results are never written to the sheet (empty output)
        
        A sensible result should have:
        - At least one VO with non-zero CPU values
        - update_cells called with non-empty cell list
        """
        # 1. Mock sheets
        mock_target_ws = MagicMock()
        mock_init.return_value = mock_target_ws
        
        # 2. Mock API with multiple VOs
        mock_get_vos.return_value = [{'name': 'vo.alice'}, {'name': 'vo.bob'}]
        
        # 3. Mock target sheet with headers already in place
        mock_target_ws.get_all_values.return_value = [['VO', '2024.01-03']]
        mock_target_ws.cell.return_value.value = 'VO'
        
        # 4. Mock API - return realistic values
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        
        # Different values for each VO
        def mock_api_response(*args, **kwargs):
            url = args[0] if args else ""
            if 'vo.alice' in url:
                mock_resp.json.return_value = [{'id': 'Total', 'Total': 1500}]
            elif 'vo.bob' in url:
                mock_resp.json.return_value = [{'id': 'Total', 'Total': 2300}]
            else:
                mock_resp.json.return_value = [{'id': 'Total', 'Total': 0}]
            return mock_resp
        
        mock_get.side_effect = mock_api_response
        
        self.app.run()
        
        # REGRESSION CHECKS:
        # 1. Board should not be empty - update_cells must be called
        self.assertTrue(mock_target_ws.update_cells.called, 
                       "Data should be written (regression: no cells updated)")
        
        # 2. Should have at least 2 VOs worth of updates
        cells = mock_target_ws.update_cells.call_args[0][0]
        self.assertGreaterEqual(len(cells), 2, 
                               "Should update at least 2 VOs worth of cells")
        
        # 3. Extract and verify values are realistic (not empty/None)
        values = [cell.value for cell in cells]
        non_empty_values = [v for v in values if v is not None and v != '']
        self.assertGreater(len(non_empty_values), 0,
                          "Some cells should contain non-empty values")
        
        # 4. Should have sensible CPU numbers (> 0)
        cpu_values = [v for v in values if isinstance(v, (int, float)) and v > 0]
        self.assertGreater(len(cpu_values), 0,
                          "Should have at least some non-zero CPU values")

if __name__ == '__main__':
    unittest.main()
