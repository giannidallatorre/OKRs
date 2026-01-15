
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
        with self.assertRaises(RuntimeError):
            self.app.fetch_accounting_data()

    def test_process_accounting_data(self):
        data = [
            {"id": "ALICE", "Total": 100, "Percent": 0.5},
            {"id": "ignored", "Total": 0, "Percent": 0}, 
            {"id": "Total", "Total": 1000, "Percent": 1.0}, # Total line
            {"id": "Percent", "Total": "", "Percent": ""}, # Invalid filtered by id
            {"id": "xlegend", "0": "ALICE"}, # Invalid filtered by missing Total
        ]
        
        summary = self.app.process_accounting_data(data)
        
        self.assertEqual(summary["total"], 1) # Only ALICE > 0
        self.assertEqual(summary["VOs_complete_list"][0]["VO name"], "ALICE")
        self.assertEqual(summary["total_cloud_cpu_hours"], 1000) # Captured from Total record
        self.assertEqual(summary["total_noVOsCPUs"], 1)
        self.assertIn("ignored", summary["noVOsCPUs"])

if __name__ == '__main__':
    unittest.main()
