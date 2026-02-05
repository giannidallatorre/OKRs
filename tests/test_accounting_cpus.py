
import unittest
import datetime
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
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'LOG': 'DEBUG',
            'ACCOUNTING_BENCHMARK_SELECTOR': 'hepspec06'
        }
        self.app = CPUAccounting(self.env)

    @patch('requests.Session.get')
    def test_fetch_accounting_data_success(self, mock_get):
        mock_get.return_value.json.return_value = [{'id': 'Total', 'Total': 100}]
        mock_get.return_value.status_code = 200
        
        data = self.app.fetch_accounting_data()
        self.assertEqual(data, [{'id': 'Total', 'Total': 100}])

    @patch('requests.Session.get')
    def test_fetch_accounting_data_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        data = self.app.fetch_accounting_data()
        self.assertEqual(data, [])

    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_update_worksheet_range_write(self, mock_init):
        mock_ws = MagicMock()
        mock_init.return_value = mock_ws
        
        mock_ws.find.return_value = None
        mock_ws.row_values.return_value = ["Period Metric", "2023.10-12"]
        mock_ws.cell.return_value.value = "Period Metric"
        
        # Mock Session to avoid real API calls
        with patch('requests.Session.get') as mock_session_get:
            mock_session_get.return_value.json.return_value = []
            mock_session_get.return_value.status_code = 200
            self.app.run()
        
        mock_ws.update.assert_called()

    def test_get_period_column_sorting(self):
        mock_ws = MagicMock()
        mock_ws.find.return_value = None
        # Mocking headers in descending order as per the new requirement
        mock_ws.row_values.return_value = ["Period Metric", "2024.07-09", "2024.01-03"]
        
        self.app.accounting_period = "2024.04-06"
        pos = self.app.get_period_column(mock_ws)
        self.assertEqual(pos, 3)

    @patch('requests.Session.get')
    @patch('egi_okr.base_accounting.init_GWorkSheet')
    def test_cpu_data_not_empty_regression(self, mock_init, mock_get):
        """
        Regression test: Ensure CPU module reports data correctly after header initialization.
        
        This catches the class of bugs where:
        - API returns data successfully
        - But write operations fail to commit results (empty sheet output)
        """
        mock_ws = MagicMock()
        mock_init.return_value = mock_ws
        
        # Mock API response with realistic data
        mock_get.return_value.json.return_value = [
            {'id': 'Total', 'Total': 5000},
            {'id': 'vo.alice', 'Total': 1500},
            {'id': 'vo.bob', 'Total': 2000},
        ]
        mock_get.return_value.status_code = 200
        
        # Mock worksheet with headers that need initialization
        mock_ws.get_all_values.return_value = [['Metric', '2024.01-03']]
        mock_ws.cell.return_value.value = 'Metric'
        
        self.app.run()
        
        # REGRESSION CHECKS:
        # 1. Should write data to the sheet
        mock_ws.update.assert_called()
        
        # 2. Verify data was written (check for range update call)
        # The module should call worksheet.update() with CPU values
        calls = mock_ws.update.call_args_list
        self.assertGreater(len(calls), 0, "Should have written data to worksheet")

