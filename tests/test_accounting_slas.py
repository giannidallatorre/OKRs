
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
            'ACCOUNTING_BENCHMARK_SELECTOR': 'hepspec06'
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
        
        # run() calls init_worksheet(target) -> then fetch_active_slas calls init_worksheet(SLA)
        mock_init.side_effect = [mock_target_ws, mock_sla_source_ws]
        
        # 2. Mock Source Data
        row = [''] * 20
        row[6] = "FINALIZED"
        row[10] = "vo.test"
        row[16] = "TRUE"
        mock_sla_source_ws.get_all_values.return_value = [['H']*20, row]
        
        # 3. Mock Target Sheet logic
        mock_target_ws.row_values.return_value = ['VO', '2023.10-12']
        mock_target_ws.get_all_values.return_value = [['VO', '2023.10-12'], ['vo.test', '0']]
        mock_target_ws.cell.return_value.value = 'vo.test'
        
        # 4. Mock API
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{'id': 'Total', 'Total': 100}]
        
        self.app.run()
        
        # Verify
        mock_target_ws.update_cells.assert_called()

if __name__ == '__main__':
    unittest.main()
