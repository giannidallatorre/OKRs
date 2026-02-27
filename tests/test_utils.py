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
    
    def test_partial_missing_dates(self):
        """Test when only one date is missing"""
        env = {'DATE_FROM': '2024/04'}
        period = format_reporting_period(env)
        # Should calculate DATE_TO as last month and succeed
        assert period != "UNKNOWN_PERIOD"
        assert period != "INVALID_PERIOD"


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
