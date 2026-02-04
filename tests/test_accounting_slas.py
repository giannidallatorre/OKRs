
import unittest
from unittest.mock import patch, MagicMock
from egi_okr.accounting_slas import SLAsAccounting

class TestSLAsAccounting(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'LOG': 'DEBUG',
            'GOOGLE_SHEET_NAME': 'dummy',
            'GOOGLE_SLAs_WORKSHEET': 'SLAs',
            'GOOGLE_SLAs_SHEET_NAME': 'SLAsSheet',
            'GOOGLE_SLAs_CLOUD_WORKSHEET': 'CloudReport',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_SERVER_URL': 'http://acc',
            'ACCOUNTING_METRIC': 'metric',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'local',
            'ACCOUNTING_BENCHMARK_SELECTOR': 'hepspec06',
            'ACCOUNTING_DATA_SELECTOR': 'data'
        }
        self.app = SLAsAccounting(self.env)

    @patch('egi_okr.accounting_slas.init_GWorkSheet')
    def test_fetch_active_slas(self, mock_init):
        # Mock SLA sheet return
        mock_ws = MagicMock()
        mock_init.return_value = mock_ws
        
        # Mock rows: Header, Empty, Valid Row
        # Indices: 0:Customer, 6:Status, 7:Start, 8:End, 10:Name, 12:EGI, 16:Cloud
        row_finalized = [''] * 20
        row_finalized[6] = "FINALIZED"
        row_finalized[10] = "vo.test"
        row_finalized[12] = "" # Not EGI
        row_finalized[16] = "TRUE" # Cloud
        row_finalized[7] = "2023/01"
        row_finalized[8] = "2025/12"
        
        mock_ws.get_all_values.return_value = [
            ['NA']*20, 
            row_finalized
        ]
        
        slas = self.app.fetch_active_slas()
        
        self.assertEqual(len(slas), 1)
        self.assertEqual(slas[0]['Name'], "vo.test")
        self.assertTrue("cloud" in slas[0]['Type'])

    @patch('egi_okr.accounting_slas.requests.get')
    @patch('egi_okr.accounting_slas.init_GWorkSheet')
    def test_run_flow(self, mock_init, mock_get):
        mock_target_ws = MagicMock()
        mock_slas_ws = MagicMock()
        
        # side_effect depends on how many times init called. 
        # main() -> get target (1st call) -> fetch_active_slas -> get SLA (2nd call).
        # So return 1st: target, 2nd: slas.
        mock_init.side_effect = [mock_target_ws, mock_slas_ws]
        
        # Mock SLAs data (Cloud Type)
        row = [''] * 20
        row[6] = "FINALIZED"
        row[10] = "vo.test"
        row[12] = "" 
        row[16] = "TRUE" # Cloud type
        row[7] = "2023/01"
        row[8] = "2025/12"
        mock_slas_ws.get_all_values.return_value = [['']*20, row]
        
        # Mock Target WS headers
        mock_target_ws.col_values.return_value = ['Period', '2023.12-12']
        mock_target_ws.row_values.return_value = ['Period', 'ExistingVO'] 
        
        # Mock Accounting Data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'id': 'Total', 'Total': 100}]
        mock_get.return_value = mock_response
        
        self.app.main()
        
        # Assertions
        mock_target_ws.insert_cols.assert_called()
        
if __name__ == '__main__':
    unittest.main()
