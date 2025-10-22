import unittest
from unittest.mock import patch
from pyOKR_VOs_CPUs_Accounting.services.service import AccountingService

class TestService(unittest.TestCase):
    """
    Test suite for the AccountingService class.
    This class contains tests for fetching accounting data from the EGI accounting server.
    """

    @patch('pyOKR_VOs_CPUs_Accounting.services.service.requests.get')
    def test_fetch_accounting_data(self, mock_get):
        """
        Test the basic functionality of fetching accounting data.
        This test checks if the service can successfully:
        1. Make a request to the accounting server
        2. Parse the JSON response
        3. Return the data correctly
        """
        mock_get.return_value.json.return_value = {'data': 'test'}
        env = {
            'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_METRIC': 'sum_elap_processors',
            'DATE_FROM': '2020/01',
            'DATE_TO': '2020/03',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'LOG': 'DEBUG'
        }
        service = AccountingService(env)
        data = service.fetch_accounting_data()
        self.assertEqual(data, {'data': 'test'})

    @patch('pyOKR_VOs_CPUs_Accounting.services.service.requests.get')
    def test_fetch_accounting_data_network_error(self, mock_get):
        """
        Test how the service handles network errors.
        This test simulates a situation where:
        1. The network connection fails
        2. The request to the accounting server fails
        3. The service should raise an exception
        
        This helps ensure the service fails gracefully when the network is down.
        """
        mock_get.side_effect = Exception("Network error")
        env = {
            'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_METRIC': 'sum_elap_processors',
            'DATE_FROM': '2020/01',
            'DATE_TO': '2020/03',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'LOG': 'DEBUG'
        }
        service = AccountingService(env)
        with self.assertRaises(Exception):
            service.fetch_accounting_data()

    @patch('pyOKR_VOs_CPUs_Accounting.services.service.requests.get')
    def test_fetch_accounting_data_malformed_response(self, mock_get):
        """
        Test how the service handles bad JSON responses.
        This test simulates a situation where:
        1. The server responds successfully
        2. But the response contains invalid JSON data
        3. The service should raise a ValueError
        
        This helps catch problems with corrupted or incorrect server responses.
        """
        mock_get.return_value.json.side_effect = ValueError("Malformed JSON")
        env = {
            'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_METRIC': 'sum_elap_processors',
            'DATE_FROM': '2020/01',
            'DATE_TO': '2020/03',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'LOG': 'DEBUG'
        }
        service = AccountingService(env)
        with self.assertRaises(ValueError):
            service.fetch_accounting_data()

    @patch('pyOKR_VOs_CPUs_Accounting.services.service.requests.get')
    def test_fetch_accounting_data_empty_response(self, mock_get):
        """
        Test how the service handles empty responses.
        This test checks if the service can handle:
        1. A response that is empty
        2. A response that contains no data
        3. Make sure it doesn't crash with empty data
        """
        mock_get.return_value.json.return_value = {}
        env = {
            'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_METRIC': 'sum_elap_processors',
            'DATE_FROM': '2020/01',
            'DATE_TO': '2020/03',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'LOG': 'DEBUG'
        }
        service = AccountingService(env)
        data = service.fetch_accounting_data()
        self.assertEqual(data, {})

    @patch('pyOKR_VOs_CPUs_Accounting.services.service.requests.get')
    def test_fetch_accounting_data_missing_env(self, mock_get):
        """
        Test how the service behaves with missing environment variables.
        This test makes sure that:
        1. The service checks for required environment variables
        2. It raises an error if important settings are missing
        3. The error message is clear about what's missing
        """
        env = {
            'LOG': 'DEBUG'  # Only providing LOG, missing all other required variables
        }
        service = AccountingService(env)
        with self.assertRaises(KeyError):
            service.fetch_accounting_data()

    @patch('pyOKR_VOs_CPUs_Accounting.services.service.requests.get')
    def test_fetch_accounting_data_timeout(self, mock_get):
        """
        Test how the service handles timeout errors.
        This test simulates:
        1. A slow server response
        2. A connection timeout
        3. Makes sure the service handles timeouts properly
        """
        mock_get.side_effect = TimeoutError("Request timed out")
        env = {
            'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_METRIC': 'sum_elap_processors',
            'DATE_FROM': '2020/01',
            'DATE_TO': '2020/03',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'LOG': 'DEBUG'
        }
        service = AccountingService(env)
        with self.assertRaises(TimeoutError):
            service.fetch_accounting_data()

if __name__ == '__main__':
    unittest.main()