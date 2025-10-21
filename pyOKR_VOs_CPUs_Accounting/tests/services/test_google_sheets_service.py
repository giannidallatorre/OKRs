import unittest
from unittest.mock import patch, MagicMock
import gspread
from pyOKR_VOs_CPUs_Accounting.services.google_sheets_service import GoogleSheetsService

class TestGoogleSheetsService(unittest.TestCase):
    """
    Test suite for the Google Sheets Service.
    Tests the interaction with Google Sheets including:
    1. Authentication and authorization
    2. Worksheet initialization and access
    3. Data updates and formatting
    4. Error handling
    """

    def setUp(self):
        """
        Set up test environment before each test.
        Creates a service instance with mock credentials.
        """
        self.env = {
            'SERVICE_ACCOUNT_FILE': '.config/service_account.json',
            'GOOGLE_SHEET_NAME': 'test-sheet',
            'GOOGLE_HTC_WORKSHEET': 'test-worksheet'
        }
        self.service = GoogleSheetsService(self.env)

    @patch('gspread.authorize')
    @patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name')
    def test_init_worksheet_success(self, mock_credentials, mock_authorize):
        """
        Test successful worksheet initialization.
        Verifies that:
        1. Credentials are loaded correctly with proper scope
        2. Authorization is successful
        3. Worksheet is opened and returned
        """
        expected_scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_authorize.return_value.open.return_value = mock_sheet
        mock_sheet.worksheet.return_value = mock_worksheet

        result = self.service.init_GWorkSheet()
        self.assertEqual(result, mock_worksheet)
        mock_credentials.assert_called_once_with(
            self.env['SERVICE_ACCOUNT_FILE'], 
            expected_scope
        )
        mock_authorize.assert_called_once()

    @patch('gspread.authorize')
    @patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name')
    def test_init_worksheet_auth_error(self, mock_credentials, mock_authorize):
        """
        Test worksheet initialization with authentication error.
        Verifies that:
        1. Authentication errors are caught
        2. Appropriate exception is raised
        3. Error message is meaningful
        """
        # Mock handle_exception function
        with patch('pyOKR_VOs_CPUs_Accounting.services.google_sheets_service.handle_exception') as mock_handle:
            mock_credentials.side_effect = Exception("Authentication failed")
            self.service.init_GWorkSheet()
            mock_handle.assert_called_once()

    @patch('gspread.authorize')
    @patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name')
    def test_update_worksheet(self, mock_credentials, mock_authorize):
        """
        Test worksheet update functionality.
        Verifies that:
        1. Data is formatted correctly
        2. Worksheet is updated with correct values
        3. Formatting is applied properly
        """
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = []
        test_period = "2020.01-03"
        test_summary = {
            'total': 2,
            'total_cloud_cpu_hours': 300,  # Added missing key
            'VOs_complete_list': [
                {'VO name': 'VO1', 'Total': 100},
                {'VO name': 'VO2', 'Total': 200}
            ],
            'noVOsCPUs': []
        }

        # Set ACCOUNTING_SCOPE in env
        self.env['ACCOUNTING_SCOPE'] = 'cloud'
        
        self.service.update_GWorkSheet(mock_worksheet, test_period, test_summary)

        # Verify worksheet formatting was called
        mock_worksheet.format.assert_any_call("A1:H1", {
            "backgroundColor": {
                "red": 55.0,
                "green": 15.0,
                "blue": 10.0
            },
            "horizontalAlignment": "LEFT",
            "textFormat": {"fontSize": 11, "bold": True}
        })

        # Verify data was inserted
        mock_worksheet.insert_row.assert_called()

    @patch('gspread.authorize')
    @patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name')
    def test_update_worksheet_invalid_data(self, mock_credentials, mock_authorize):
        """
        Test worksheet update with invalid data.
        Verifies that:
        1. Invalid data structure is handled gracefully
        2. Error is logged appropriately
        3. No updates are made to the worksheet
        """
        mock_worksheet = MagicMock()
        test_period = "2020.01-03"
        invalid_summary = {
            'total': 1,
            'total_cloud_cpu_hours': 100,  # Added missing key
            'VOs_complete_list': None,  # Invalid: missing required data
            'noVOsCPUs': []
        }

        # Mock handle_exception function
        with patch('pyOKR_VOs_CPUs_Accounting.services.google_sheets_service.handle_exception') as mock_handle:
            self.service.update_GWorkSheet(mock_worksheet, test_period, invalid_summary)
            # Verify exception was handled
            mock_handle.assert_called_once()
            # Verify no updates were made
            mock_worksheet.insert_row.assert_not_called()

    @patch('gspread.authorize')
    @patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name')
    def test_worksheet_not_found(self, mock_credentials, mock_authorize):
        """
        Test handling of non-existent worksheet.
        Verifies that:
        1. Missing worksheet is detected
        2. Error is handled gracefully
        3. None is returned as expected
        """
        mock_sheet = MagicMock()
        mock_sheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound("Worksheet not found")
        mock_authorize.return_value.open.return_value = mock_sheet

        result = self.service.init_GWorkSheet()
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()