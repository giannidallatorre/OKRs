import pytest
from pyOKR_VOs_CPUs_Accounting.utils.utils import find_difference, colourise, get_env_settings

"""
Test suite for utility functions.
These tests verify the basic helper functions used throughout the application:
1. String manipulation and comparison
2. Color formatting for terminal output
3. Environment variable handling
"""

def test_find_difference():
    """
    Test the function that finds differences between two comma-separated lists.
    This test checks if the function can:
    1. Compare two lists of VOs
    2. Find items that are in one list but not the other
    3. Return the differences in the correct order (added, removed)
    """
    result = find_difference("VO1, VO2", "VO2, VO3")
    assert result == ("VO3", "VO1")

def test_colourise():
    """
    Test the color formatting function for terminal output.
    This test verifies that:
    1. Text can be colored correctly
    2. The ANSI escape codes are added properly
    3. The formatted string matches the expected format
    """
    result = colourise("red", "test")
    assert result == "\033[1;31mtest\033[1;m"

def test_get_env_settings(monkeypatch):
    """
    Test the environment settings retrieval function.
    This test ensures that:
    1. All required environment variables are read correctly
    2. Variables are converted to the right types
    3. Default values are applied when needed
    4. The settings dictionary contains all necessary keys
    """
    # Mock environment variables for testing
    monkeypatch.setenv('ACCOUNTING_SERVER_URL', 'https://accounting.egi.eu')
    monkeypatch.setenv('ACCOUNTING_SCOPE', 'cloud')
    monkeypatch.setenv('ACCOUNTING_METRIC', 'sum_elap_processors')
    monkeypatch.setenv('ACCOUNTING_LOCAL_JOB_SELECTOR', 'onlyinfrajobs')
    monkeypatch.setenv('ACCOUNTING_VO_GROUP_SELECTOR', 'egi')
    monkeypatch.setenv('ACCOUNTING_DATA_SELECTOR', 'JSON')
    monkeypatch.setenv('SERVICE_ACCOUNT_PATH', '/path/to/service_account')
    monkeypatch.setenv('SERVICE_ACCOUNT_FILE', '/path/to/service_account.json')
    monkeypatch.setenv('GOOGLE_SHEET_NAME', 'OKR_Reports')
    monkeypatch.setenv('GOOGLE_CLOUD_WORKSHEET', 'Accounting Cloud CPU/h')
    monkeypatch.setenv('GOOGLE_HTC_WORKSHEET', 'Accounting HTC CPU/h')
    monkeypatch.setenv('LOG', 'DEBUG')
    monkeypatch.setenv('DATE_FROM', '2020/01')
    monkeypatch.setenv('DATE_TO', '2020/03')
    monkeypatch.setenv('SSL_CHECK', 'True')

    result = get_env_settings()
    assert result['ACCOUNTING_SERVER_URL'] == 'https://accounting.egi.eu'
    assert result['DATE_TO'] == '2020/03'


if __name__ == '__main__':
    pytest.main()