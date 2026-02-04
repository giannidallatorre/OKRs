
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
from egi_okr.operations import get_VOs_stats

class TestOperationsExtended(unittest.TestCase):
    def setUp(self):
        self.env = {
            'OPERATIONS_SERVER_URL': 'http://api.test',
            'OPERATIONS_API_KEY': 'dummy_key',
            'OPERATIONS_FORMAT': 'json',
            'OPERATIONS_VO_LIST_PREFIX': '/vo-list',
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'LOG': 'DEBUG'
        }

    @patch('egi_okr.operations.requests.get')
    def test_get_VOs_stats_api_failure(self, mock_get):
        # Mock 401 Unauthorized
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        # Ensure cache check returns False
        with patch('os.path.exists', return_value=False):
            stats = get_VOs_stats(self.env)
            self.assertEqual(stats, [])

    @patch('egi_okr.operations.requests.get')
    def test_get_VOs_stats_caching_logic(self, mock_get):
        # 1. Mock API response
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {
            "data": [{"name": "vo1", "scope": "eosc", "homeUrl": "http://vo1"}]
        }
        mock_get.return_value = mock_api_response
        
        # 2. Mock VO user fetch
        with patch('egi_okr.operations.get_VO_users', return_value="10"), \
             patch('egi_okr.operations.get_VO_metadata', return_value=("st", "url", 1)):
            
            # First call: No cache exists
            with patch('os.path.exists', return_value=False), \
                 patch('os.makedirs'), \
                 patch('builtins.open', mock_open()) as mocked_file:
                
                stats1 = get_VOs_stats(self.env)
                self.assertEqual(len(stats1), 1)
                self.assertEqual(mock_get.call_count, 1)
                # Verify it tried to save to cache
                mocked_file.assert_called()

            # Second call: Cache exists
            cached_data = [{"name": "vo1", "users": 10}]
            with patch('os.path.exists', return_value=True), \
                 patch('builtins.open', mock_open(read_data=json.dumps(cached_data))):
                
                stats2 = get_VOs_stats(self.env)
                self.assertEqual(len(stats2), 1)
                # mock_get should NOT have been called again
                self.assertEqual(mock_get.call_count, 1)

if __name__ == '__main__':
    unittest.main()
