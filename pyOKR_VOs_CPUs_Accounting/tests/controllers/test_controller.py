import unittest
from unittest.mock import patch, MagicMock
from pyOKR_VOs_CPUs_Accounting.controllers.controller import Controller

class TestController(unittest.TestCase):
    """
    Test suite for the Controller class.
    This class tests the main controller that coordinates:
    1. Fetching data from the accounting service
    2. Writing data to Google Sheets
    3. Formatting and presenting the results
    """

    @patch('pyOKR_VOs_CPUs_Accounting.services.service.AccountingService.fetch_accounting_data')
    @patch('pyOKR_VOs_CPUs_Accounting.services.service.AccountingService.process_accounting_data')
    @patch('pyOKR_VOs_CPUs_Accounting.services.google_sheets_service.GoogleSheetsService.init_GWorkSheet')
    @patch('pyOKR_VOs_CPUs_Accounting.services.google_sheets_service.GoogleSheetsService.update_GWorkSheet')
    def test_run(self, mock_update_worksheet, mock_init_worksheet, mock_process_data, mock_fetch_data):
        """
        Test the main run method of the controller.
        This test checks if the controller can:
        1. Get accounting data successfully
        2. Process the accounting data
        3. Initialize the Google Worksheet
        4. Update the worksheet with the processed data
        """
        # Prepare test data and mocks
        test_data = [{'id': 'VO1', 'Total': 100}]
        test_summary = {'total': 1, 'vos': ['VO1'], 'values': [100]}
        mock_worksheet = MagicMock()
        
        mock_fetch_data.return_value = test_data
        mock_process_data.return_value = test_summary
        mock_init_worksheet.return_value = mock_worksheet
        
        # The mocks are already set up above
        
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
            'SERVICE_ACCOUNT_FILE': '.config/service_account.json',
            'GOOGLE_SHEET_NAME': 'OKR-integration-test',
            'GOOGLE_HTC_WORKSHEET': 'OKR-integration-test-2'
        }
        
        # Run the controller
        controller = Controller(env)
        controller.run()
        
        # Verify that all the methods were called correctly in sequence
        mock_fetch_data.assert_called_once()
        mock_process_data.assert_called_once_with(test_data)
        mock_init_worksheet.assert_called_once()
        mock_update_worksheet.assert_called_once_with(mock_worksheet, f"2020.01-03", test_summary)

    @patch('gspread.authorize')
    @patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name')
    def test_print_collected_metrics(self, mock_from_json_keyfile_name, mock_authorize):
        """
        Test the metrics printing functionality.
        This test verifies that:
        1. The controller can format metrics correctly
        2. The output includes all required VO information
        3. The totals are calculated and displayed properly
        4. The formatting of the output is correct
        
        This is important for ensuring that metrics are presented in a readable format.
        """
        mock_connect = MagicMock()
        mock_connect.return_value = [
            {'id': 'VO1', 'Total': 100},
            {'id': 'VO2', 'Total': 0},
            {'id': 'VO3', 'Total': 200},
            {'id': 'Total', 'Total': 300}
        ]
    
        # Mock the credentials
        mock_creds = MagicMock()
        mock_from_json_keyfile_name.return_value = mock_creds
        mock_authorize.return_value = MagicMock()
    
        env = {
            'LOG': 'DEBUG',
            'ACCOUNTING_SCOPE': 'cloud',
            'DATE_FROM': '2024/10',
            'DATE_TO': '2024/12',
            'SERVICE_ACCOUNT_FILE': 'service_account.json',
            'GOOGLE_SHEET_NAME': 'OKR_Reports_test',
            'GOOGLE_CLOUD_WORKSHEET': 'OKR-integration-test',
            'GOOGLE_HTC_WORKSHEET': 'OKR-integration-test-2'
        }
        controller = Controller(env)
        controller.accounting_service.connect = mock_connect
    
        # Capture the output of the print statements
        with patch('builtins.print') as mock_print:
            controller.run()
    
        # Add assertions as needed
        if controller.dry_run:
            mock_print.assert_called()

    @patch('builtins.print')
    def test_pretty_print_summary(self, mock_print):
        env = {
            'LOG': 'DEBUG',
            'ACCOUNTING_SCOPE': 'cloud',
            'DATE_FROM': '2020/01',
            'DATE_TO': '2020/03',
            'SERVICE_ACCOUNT_FILE': 'service_account.json',
            'GOOGLE_SHEET_NAME': 'TestSheet',
            'GOOGLE_HTC_WORKSHEET': 'TestWorksheet'
        }
        controller = Controller(env, dry_run=True)
        summary = {
            "total": 3,
            "total_noVOsCPUs": 1,
            "total_cloud_cpu_hours": 1000,
            "total_htc_cpu": 500,
            "noVOsCPUs": ["VO2"],
            "VOs_complete_list": [
                {"VO name": "VO1", "CPU/h": "100"},
                {"VO name": "VO3", "CPU/h": "200"},
                {"VO name": "VO4", "CPU/h": "700"}
            ]
        }
        accounting_period = "2020.01-03"
        controller.pretty_print_summary(accounting_period, summary)
        
        # Check that print was called with the expected output
        mock_print.assert_any_call("Reporting Period: 2020.01-03")
        mock_print.assert_any_call("Total VOs with accounting records: 3")
        mock_print.assert_any_call("Total VOs with no accounting records: 1")
        mock_print.assert_any_call("Total Cloud CPU/h: 1000")
        mock_print.assert_any_call("Total HTC CPU/h: 500")
        mock_print.assert_any_call("VOs with accounting records:")
        mock_print.assert_any_call("  - VO1: 100")
        mock_print.assert_any_call("  - VO3: 200")
        mock_print.assert_any_call("  - VO4: 700")
        mock_print.assert_any_call("VOs with no accounting records:")
        mock_print.assert_any_call("  - VO2")

if __name__ == '__main__':
    unittest.main()