
import unittest
from unittest.mock import patch, MagicMock
import requests
from egi_okr.accounting_cpus import CPUAccounting

class TestCPUAccounting(unittest.TestCase):
    def setUp(self):
        self.env = {
            'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_METRIC': 'sum_elap_processors',
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
            'ACCOUNTING_BENCHMARK_SELECTOR': 'hepspec06',
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'LOG': 'DEBUG'
        }
        self.app = CPUAccounting(self.env)

    @patch('egi_okr.accounting_cpus.requests.get')
    def test_fetch_accounting_data_success(self, mock_get):
        mock_get.return_value.json.return_value = [{'id': 'Total', 'Total': 100}]
        mock_get.return_value.status_code = 200
        
        data = self.app.fetch_accounting_data()
        self.assertEqual(data, [{'id': 'Total', 'Total': 100}])

    @patch('egi_okr.accounting_cpus.requests.get')
    def test_fetch_accounting_data_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        data = self.app.fetch_accounting_data()
        self.assertEqual(data, [])


    @patch('egi_okr.accounting_cpus.init_GWorkSheet')
    def test_update_worksheet_range_write(self, mock_init):
        mock_ws = MagicMock()
        mock_init.return_value = mock_ws
        
        # Mocking orientation labels already present
        mock_ws.col_values.return_value = ["Period Metric", "Cloud CPU/h"]
        # Mocking some existing periods in header
        mock_ws.row_values.return_value = ["Period Metric", "2023.10-12"] 
        
        summary = {
            "total": 10,
            "total_cloud_cpu_hours": 5000,
            "total_htc_cpu": 0,
            "noVOsCPUs": ["vo.bad"],
            "VOs_complete_list": [{"VO name": "vo.good"}]
        }
        
        # Run
        self.app.update_worksheet(summary)
        
        # Verify range based update (e.g. B2:B8 if period_col=3)
        # 2024.01-03 should be inserted after 2023.10-12 -> col 3
        mock_ws.insert_cols.assert_called()
        mock_ws.update.assert_called()
        
        # Check that update was called with a vertical range
        args, kwargs = mock_ws.update.call_args
        target_range = args[0]
        # Column C is '3' in index
        self.assertIn("C2:C8", target_range)

    def test_get_period_col_position_sorting(self):
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = ["Period Metric", "2024.01-03", "2024.07-09"]
        
        # 1. Middle insertion
        pos, found = self.app.get_period_col_position(mock_ws, "2024.04-06")
        self.assertEqual(pos, 3)
        self.assertFalse(found)
        
        # 2. Existing
        pos, found = self.app.get_period_col_position(mock_ws, "2024.01-03")
        self.assertEqual(pos, 2)
        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
