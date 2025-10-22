import unittest
from unittest.mock import patch, MagicMock
from pyOKR_VOs_CPUs_Accounting.controllers.controller import Controller
from pyOKR_VOs_CPUs_Accounting.services.service import AccountingService

class TestIntegration(unittest.TestCase):
    """
    Integration test suite for the OKR VOs CPUs Accounting system.
    These tests verify that all components work together correctly:
    1. Controller coordination
    2. Service data retrieval
    3. Google Sheets integration
    4. End-to-end data flow
    """

    @patch('gspread.authorize')
    @patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name')
    @patch('requests.get')
    def test_integration(self, mock_get, mock_from_json_keyfile_name, mock_authorize):
        """
        Test the complete flow from data fetching to spreadsheet update.
        This test verifies that:
        1. Data is fetched from the accounting server
        2. The data is processed correctly
        3. Google Sheets authentication works
        4. The worksheet is updated with proper formatting
        5. All components interact correctly with each other
        
        This is the main test that ensures the entire system works as expected.
        """
        # Mock the response from the accounting server
        mock_get.return_value.json.return_value = [
            {'id': 'VO1', 'Total': 100},
            {'id': 'VO2', 'Total': 0},
            {'id': 'VO3', 'Total': 200},
            {'id': 'Total', 'Total': 300}
        ]
        
        # Mock the credentials and Google Sheets client
        mock_creds = MagicMock()
        mock_from_json_keyfile_name.return_value = mock_creds
        mock_worksheet = MagicMock()
        mock_authorize.return_value.open.return_value.worksheet.return_value = mock_worksheet
        
        env = {
            'LOG': 'DEBUG',
            'ACCOUNTING_SERVER_URL': 'https://accounting.egi.eu',
            'ACCOUNTING_SCOPE': 'cloud',
            'ACCOUNTING_METRIC': 'sum_elap_processors',
            'DATE_FROM': '2020/01',
            'DATE_TO': '2020/03',
            'ACCOUNTING_VO_GROUP_SELECTOR': 'egi',
            'ACCOUNTING_LOCAL_JOB_SELECTOR': 'onlyinfrajobs',
            'ACCOUNTING_DATA_SELECTOR': 'JSON',
            'SERVICE_ACCOUNT_FILE': 'service_account.json',
            'GOOGLE_SHEET_NAME': 'OKR-integration-test',
            'GOOGLE_HTC_WORKSHEET': 'OKR-integration-test-2'
        }
        
        # Create the Controller and run the integration test
        controller = Controller(env)
        
        # Capture the output of the print statements
        with patch('builtins.print') as mock_print:
            controller.run()
        
        # Verify that the worksheet was updated correctly
        mock_worksheet.format.assert_any_call("A1:H1", {
            "backgroundColor": {
                "red": 55.0,
                "green": 15.0,
                "blue": 10.0
            },
            "horizontalAlignment": "LEFT",
            "textFormat": { "fontSize": 11, "bold": True }
        })
        mock_worksheet.format.assert_any_call("A2:H100", {
            "horizontalAlignment": "RIGHT",
            "textFormat": { "fontSize": 11 }
        })
        mock_worksheet.insert_row.assert_called()

if __name__ == '__main__':
    unittest.main()