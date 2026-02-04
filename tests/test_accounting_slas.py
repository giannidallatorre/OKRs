
import unittest
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

    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_fetch_active_slas(self, mock_init):
        mock_ws = MagicMock()
        mock_init.return_value = mock_ws
        
        # Row 10: vo.test, Row 16: TRUE
        row = [''] * 20
        row[6] = "FINALIZED"
        row[10] = "vo.test"
        row[16] = "TRUE"
        mock_ws.get_all_values.return_value = [['H']*20, row]
        
        slas = self.app.fetch_active_slas()
        self.assertEqual(len(slas), 1)
        self.assertEqual(slas[0]['Name'], "vo.test")

    @patch('egi_okr.accounting_slas.requests.get')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_run_flow(self, mock_init, mock_get):
        # 1. Mock Sheets
        mock_target_ws = MagicMock()
        mock_sla_source_ws = MagicMock()
        mock_init.side_effect = [mock_target_ws, mock_sla_source_ws]
        
        # 2. Mock Source Data (SLA sheet)
        row = [''] * 20
        row[0] = "Customer X"
        row[6] = "FINALIZED"
        row[10] = "vo.test"
        row[16] = "TRUE"
        mock_sla_source_ws.get_all_values.return_value = [['H']*20, row]
        
        # 3. Mock Target Sheet (Results sheet)
        mock_target_ws.get_all_values.return_value = [['VO', '2023.10-12']]
        
        # 4. Mock API (Individual VO fetch)
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

if __name__ == '__main__':
    unittest.main()
