
import unittest
import os
import json
import requests
from unittest.mock import patch, MagicMock
from egi_okr.utils import _load_process_cache, _save_process_cache, clear_connection_cache, init_GWorkSheet
from egi_okr.operations import get_VOs_stats

class TestPerformanceFeatures(unittest.TestCase):
    def setUp(self):
        self.test_cache = ".test_conn_cache.json"
        # Patch the constant in the module
        self.patcher = patch('egi_okr.utils._CACHE_FILE', self.test_cache)
        self.patcher.start()
        clear_connection_cache()

    def tearDown(self):
        clear_connection_cache()
        self.patcher.stop()

    def test_persistent_cache_lifecycle(self):
        """Verify that cache persists across loads and saves."""
        data = {"connections": {"test_id": {"title": "Test Sheet", "url": "http://test"}}, "shared": ["id:user"]}
        _save_process_cache(data)
        
        loaded = _load_process_cache()
        self.assertEqual(loaded["connections"]["test_id"]["title"], "Test Sheet")
        self.assertIn("id:user", loaded["shared"])

    @patch('egi_okr.utils.init_google_credentials')
    def test_init_GWorkSheet_logging_suppression(self, mock_creds):
        """Verify that connection info is printed only once (cached)."""
        env = {'GOOGLE_SHEET_NAME': 'TestSheet', 'USER_EMAIL': 'user@test', 'TEST_WS': 'Sheet1'}
        mock_account = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.id = "unique_id"
        mock_sheet.title = "TestSheet"
        mock_sheet.url = "http://test"
        mock_account.open.return_value = mock_sheet
        mock_creds.return_value = mock_account

        with patch('builtins.print') as mock_print:
            # First call: should print
            init_GWorkSheet(env, 'TEST_WS')
            # Check if "[INFO] Connected to Spreadsheet" was printed
            printed_texts = [call[0][1] for call in mock_print.call_args_list if len(call[0]) > 1]
            self.assertTrue(any("Connected to Spreadsheet" in str(t) for t in printed_texts))
            
            mock_print.reset_mock()
            
            # Second call: should NOT print connection info
            init_GWorkSheet(env, 'TEST_WS')
            printed_texts = [call[0][1] for call in mock_print.call_args_list if len(call[0]) > 1]
            self.assertFalse(any("Connected to Spreadsheet" in str(t) for t in printed_texts))

    @patch('egi_okr.operations.get_VO_metadata')
    @patch('egi_okr.operations.get_VO_users')
    @patch('requests.Session.get')
    def test_parallel_vo_fetching(self, mock_get, mock_users, mock_metadata):
        """Verify that VOs are fetched in parallel (multiple calls made)."""
        env = {
            'OPERATIONS_SERVER_URL': 'http://ops',
            'OPERATIONS_VO_LIST_PREFIX': '/list',
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03'
        }
        mock_session = requests.Session()
        
        # 1. Mock VO List
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'data': [
                {'name': 'vo1', 'scope': 'egi', 'homeUrl': 'http://vo1'},
                {'name': 'vo2', 'scope': 'egi', 'homeUrl': 'http://vo2'},
                {'name': 'vo3', 'scope': 'egi', 'homeUrl': 'http://vo3'}
            ]
        }
        mock_get.return_value = mock_resp
        
        # 2. Mock individual fetches
        mock_metadata.return_value = ("Ack", "Url", 1)
        mock_users.return_value = "10"
        
        # 3. Call get_VOs_stats
        with patch('os.path.exists', return_value=False): # Bypass cache
            stats = get_VOs_stats(env, session=mock_session)
            
        self.assertEqual(len(stats), 3)
        self.assertEqual(mock_metadata.call_count, 3)
        self.assertEqual(mock_users.call_count, 3)

if __name__ == '__main__':
    unittest.main()
