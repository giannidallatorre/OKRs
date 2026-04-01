import unittest
#!/usr/bin/env python3
"""
Unit tests for egi_okr.utils module focusing on configuration and validation.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch, MagicMock
from egi_okr.utils import validate_date_format, format_reporting_period, get_env_settings


class TestValidateDateFormat:
    """Test date format validation function"""
    
    def test_valid_yyyy_mm_format(self):
        """Test valid YYYY/MM format"""
        valid, normalized, error = validate_date_format("2024/04", "TEST")
        assert valid is True
        assert normalized == "2024/04"
        assert error is None
    
    def test_valid_yyyy_dash_mm_format(self):
        """Test valid YYYY-MM format"""
        valid, normalized, error = validate_date_format("2024-06", "TEST")
        assert valid is True
        assert normalized == "2024/06"
        assert error is None
    
    def test_empty_date(self):
        """Test empty date string"""
        valid, normalized, error = validate_date_format("", "TEST")
        assert valid is False
        assert normalized is None
        assert "empty" in error.lower()
    
    def test_invalid_year_length(self):
        """Test invalid year (not 4 digits)"""
        valid, normalized, error = validate_date_format("24/04", "TEST")
        assert valid is False
        assert error is not None
        assert "year must be 4 digits" in error.lower()
    
    def test_invalid_month_length(self):
        """Test invalid month (not 2 digits)"""
        valid, normalized, error = validate_date_format("2024/4", "TEST")
        assert valid is False
        assert error is not None
        assert "month must be 2 digits" in error.lower()
    
    def test_invalid_month_value_low(self):
        """Test invalid month value (< 01)"""
        valid, normalized, error = validate_date_format("2024/00", "TEST")
        assert valid is False
        assert error is not None
        assert "month must be 01-12" in error.lower()
    
    def test_invalid_month_value_high(self):
        """Test invalid month value (> 12)"""
        valid, normalized, error = validate_date_format("2024/13", "TEST")
        assert valid is False
        assert error is not None
        assert "month must be 01-12" in error.lower()
    
    def test_invalid_format_no_separator(self):
        """Test invalid format with no separator"""
        valid, normalized, error = validate_date_format("202404", "TEST")
        assert valid is False
        assert error is not None
        assert "invalid format" in error.lower()
    
    def test_invalid_format_too_many_parts(self):
        """Test invalid format with too many parts"""
        valid, normalized, error = validate_date_format("2024/04/01", "TEST")
        assert valid is False
        assert error is not None
        assert "invalid format" in error.lower()
    
    def test_invalid_year_nonnumeric(self):
        """Test invalid year with non-numeric characters"""
        valid, normalized, error = validate_date_format("abcd/04", "TEST")
        assert valid is False
        assert error is not None
        assert "year must be 4 digits" in error.lower()
    
    def test_custom_field_name_in_error(self):
        """Test that custom field name appears in error message"""
        valid, normalized, error = validate_date_format("invalid", "CUSTOM_FIELD")
        assert valid is False
        assert "CUSTOM_FIELD" in error


class TestFormatReportingPeriod:
    """Test reporting period formatting function"""
    
    def test_valid_reporting_period(self):
        """Test valid reporting period format"""
        env = {'DATE_FROM': '2024/04', 'DATE_TO': '2024/06'}
        period = format_reporting_period(env)
        assert period == "2024.04-06"
    
    def test_valid_reporting_period_dash_format(self):
        """Test valid reporting period with dash format"""
        env = {'DATE_FROM': '2024-04', 'DATE_TO': '2024-06'}
        period = format_reporting_period(env)
        assert period == "2024.04-06"
    
    def test_invalid_date_from_format(self):
        """Test invalid DATE_FROM format"""
        env = {'DATE_FROM': 'invalid', 'DATE_TO': '2024/06'}
        period = format_reporting_period(env)
        assert period == "INVALID_PERIOD"
    
    def test_invalid_date_to_format(self):
        """Test invalid DATE_TO format"""
        env = {'DATE_FROM': '2024/04', 'DATE_TO': 'invalid'}
        period = format_reporting_period(env)
        assert period == "INVALID_PERIOD"
    
    def test_missing_dates_fallback(self):
        """Test fallback when dates are missing"""
        env = {}
        period = format_reporting_period(env)
        # Should calculate last month and return valid period
        assert period != "UNKNOWN_PERIOD"
        assert "." in period  # Should contain the dot separator
        assert "-" in period  # Should contain the month range separator
    
    def test_partial_missing_dates_with_print_mode(self):
        """Test partial dates when PRINT_MODE is enabled to avoid quarter validation failures"""
        env = {'DATE_FROM': '2024/04', 'PRINT_MODE': 'True'}
        period = format_reporting_period(env)
        # Should calculate DATE_TO as last quarter's end and succeed in print mode
        assert period != "UNKNOWN_PERIOD"
        assert period != "INVALID_PERIOD"

    def test_quarter_validation_enforced(self):
        """Test that non-quarter period is rejected when not in print mode"""
        env = {'DATE_FROM': '2024/01', 'DATE_TO': '2024/02'}
        period = format_reporting_period(env)
        assert period == "INVALID_PERIOD"

    def test_quarter_validation_bypassed_in_print_mode(self):
        """Test that non-quarter period is accepted when PRINT_MODE is True"""
        env = {'DATE_FROM': '2024/01', 'DATE_TO': '2024/02', 'PRINT_MODE': 'True'}
        period = format_reporting_period(env)
        assert period == "2024.01-02"

    def test_future_quarter_rejected(self):
        """Test that valid quarter is rejected if it has not completed yet"""
        import datetime
        today = datetime.date.today()
        # A quarter in the next year will definitely not be completed
        env = {'DATE_FROM': f'{today.year + 1}/04', 'DATE_TO': f'{today.year + 1}/06'}
        period = format_reporting_period(env)
        assert period == "INVALID_PERIOD"

    def test_completed_quarter_accepted(self):
        """Test that valid completed quarter is accepted"""
        import datetime
        today = datetime.date.today()
        # A quarter in the previous year is definitely completed
        env = {'DATE_FROM': f'{today.year - 1}/04', 'DATE_TO': f'{today.year - 1}/06'}
        period = format_reporting_period(env)
        assert period == f"{today.year - 1}.04-06"

class TestGetEnvSettings:
    """Test environment settings configuration with cascading defaults"""
    
    def test_default_values_present(self):
        """Test that all default values are present"""
        # Temporarily clear relevant env vars
        original_env = {}
        keys_to_test = ['JIRA_PROJECT', 'GOOGLE_SHEET_NAME', 'ACCOUNTING_SERVER_URL']
        
        for key in keys_to_test:
            original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
        
        try:
            with patch('dotenv.load_dotenv'):
                settings = get_env_settings()
            
            # Verify defaults are present
            assert settings['JIRA_PROJECT'] == 'EOSC'
            assert settings['GOOGLE_SHEET_NAME'] == 'EGI_OKR_Test_Verify'
            assert settings['ACCOUNTING_SERVER_URL'] == 'https://accounting.egi.eu'
        finally:
            # Restore env vars
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
    
    def test_env_override_defaults(self):
        """Test that environment variables override defaults"""
        os.environ['JIRA_PROJECT'] = 'TEST_PROJECT'
        os.environ['GOOGLE_SHEET_NAME'] = 'TEST_SHEET'
        
        try:
            settings = get_env_settings()
            assert settings['JIRA_PROJECT'] == 'TEST_PROJECT'
            assert settings['GOOGLE_SHEET_NAME'] == 'TEST_SHEET'
        finally:
            del os.environ['JIRA_PROJECT']
            del os.environ['GOOGLE_SHEET_NAME']
    
    def test_jira_project_cascades_to_projectkeys(self):
        """Test that JIRA_PROJECT cascades to specific projectkeys"""
        os.environ['JIRA_PROJECT'] = 'CASCADE_TEST'
        
        try:
            settings = get_env_settings()
            # Should cascade to projectkeys
            assert settings['SERVICE_ORDERS_PROJECTKEY'] == 'CASCADE_TEST'
            assert settings['COMPLAINS_PROJECTKEY'] == 'CASCADE_TEST'
            assert settings['VIOLATIONS_PROJECTKEY'] == 'CASCADE_TEST'
        finally:
            del os.environ['JIRA_PROJECT']
    
    def test_jira_projectkey_override_cascade(self):
        """Test that explicit projectkey overrides JIRA_PROJECT cascade"""
        os.environ['JIRA_PROJECT'] = 'CASCADE_PROJECT'
        os.environ['SERVICE_ORDERS_PROJECTKEY'] = 'EXPLICIT_ORDERS'
        
        try:
            settings = get_env_settings()
            # Explicit value should not be overridden
            assert settings['SERVICE_ORDERS_PROJECTKEY'] == 'EXPLICIT_ORDERS'
            # Others should cascade
            assert settings['COMPLAINS_PROJECTKEY'] == 'CASCADE_PROJECT'
        finally:
            if 'JIRA_PROJECT' in os.environ:
                del os.environ['JIRA_PROJECT']
            if 'SERVICE_ORDERS_PROJECTKEY' in os.environ:
                del os.environ['SERVICE_ORDERS_PROJECTKEY']
    
    def test_google_slas_sheet_cascades_from_sheet_name(self):
        """Test that GOOGLE_SLAs_SHEET_NAME can be explicitly set"""
        original_slas = os.environ.get('GOOGLE_SLAs_SHEET_NAME')
        original_sheet = os.environ.get('GOOGLE_SHEET_NAME')
        
        # Set both explicitly
        os.environ['GOOGLE_SHEET_NAME'] = 'MAIN_SHEET'
        os.environ['GOOGLE_SLAs_SHEET_NAME'] = 'SLAs_SHEET'
        
        try:
            settings = get_env_settings()
            # Both should be independent when explicitly set
            assert settings['GOOGLE_SHEET_NAME'] == 'MAIN_SHEET'
            assert settings['GOOGLE_SLAs_SHEET_NAME'] == 'SLAs_SHEET'
        finally:
            if original_sheet:
                os.environ['GOOGLE_SHEET_NAME'] = original_sheet
            elif 'GOOGLE_SHEET_NAME' in os.environ:
                del os.environ['GOOGLE_SHEET_NAME']
            
            if original_slas:
                os.environ['GOOGLE_SLAs_SHEET_NAME'] = original_slas
            elif 'GOOGLE_SLAs_SHEET_NAME' in os.environ:
                del os.environ['GOOGLE_SLAs_SHEET_NAME']
    
    def test_service_account_file_default(self):
        """Test SERVICE_ACCOUNT_FILE has correct default"""
        original = os.environ.get('SERVICE_ACCOUNT_FILE')
        if 'SERVICE_ACCOUNT_FILE' in os.environ:
            del os.environ['SERVICE_ACCOUNT_FILE']
        
        try:
            settings = get_env_settings()
            assert settings['SERVICE_ACCOUNT_FILE'] == '.config/service_account.json'
        finally:
            if original:
                os.environ['SERVICE_ACCOUNT_FILE'] = original


from unittest.mock import patch, MagicMock
import os
import gspread
import logging
from egi_okr.utils import init_GWorkSheet, handle_exception, colourise

class TestUtilsExtended(unittest.TestCase):
    def setUp(self):
        self.env = {
            'GOOGLE_SHEET_NAME': 'test_sheet',
            'WORKSHEET_NAME': 'test_ws',
            'USER_EMAIL': 'user@example.com',
            'LOG': 'DEBUG'
        }

    @patch('egi_okr.utils.init_google_credentials')
    def test_init_GWorkSheet_creation_and_sharing(self, mock_creds):
        mock_account = MagicMock()
        mock_creds.return_value = mock_account
        
        # 1. Mock Spreadsheet not found, then created
        mock_sheet = MagicMock()
        mock_sheet.id = "sheet_123"
        mock_sheet.url = "http://sheet"
        mock_account.open.side_effect = gspread.exceptions.SpreadsheetNotFound
        mock_account.create.return_value = mock_sheet
        
        # 2. Mock Worksheet
        mock_ws = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        
        # Run
        ws = init_GWorkSheet(self.env, 'WORKSHEET_NAME', 'GOOGLE_SHEET_NAME')
        
        # Verify
        mock_account.create.assert_called_with('test_sheet')
        mock_sheet.share.assert_called_with('user@example.com', perm_type='user', role='writer', notify=True)
        self.assertEqual(ws, mock_ws)

    @patch('egi_okr.utils.init_google_credentials')
    def test_init_GWorkSheet_existing_silent_sharing(self, mock_creds):
        mock_account = MagicMock()
        mock_creds.return_value = mock_account
        
        mock_sheet = MagicMock()
        mock_sheet.id = "sheet_456"
        mock_account.open.return_value = mock_sheet
        
        # Clear cache for deterministic test
        import egi_okr.utils
        if hasattr(egi_okr.utils, '_SHARED_CACHE'):
            egi_okr.utils._SHARED_CACHE.clear()
            
        # Run
        init_GWorkSheet(self.env, 'WORKSHEET_NAME', 'GOOGLE_SHEET_NAME')
        
        # Verify notify=False for existing sheet
        mock_sheet.share.assert_called_with('user@example.com', perm_type='user', role='writer', notify=False)

    def test_colourise_logic(self):
        self.assertIn("\033[1;32m", colourise("green", "test"))
        self.assertEqual(colourise("unknown", "test"), "test")

    @patch('logging.error')
    @patch('logging.debug')
    def test_handle_exception_debug(self, mock_debug, mock_error):
        # Force debug level
        logging.getLogger().setLevel(logging.DEBUG)
        
        e = ValueError("test error message")
        handle_exception(e, self.env)
        
        # Verify error logged
        mock_error.assert_any_call("ERROR: test error message")
        # Verify debug (traceback) logged
        mock_debug.assert_any_call("\n[DEBUG] Traceback:")

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


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
