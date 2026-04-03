import pytest
from unittest.mock import MagicMock, patch
from egi_okr.utils import init_GWorkSheet

class TestSharingLogic:
    @patch('egi_okr.utils.init_google_credentials')
    @patch('egi_okr.utils._load_process_cache')
    @patch('egi_okr.utils._save_process_cache')
    def test_init_GWorkSheet_multiple_emails(self, mock_save, mock_load, mock_creds):
        """
        Verify that init_GWorkSheet correctly identifies, parses and shares
        with multiple emails from GOOGLE_SHARE_EMAILS.
        """
        # 1. Setup
        env = {
            'GOOGLE_SHEET_NAME': 'Test Sheet',
            'GOOGLE_SHARE_EMAILS': 'user1@example.com, user2@example.com user3@example.com',
            'TEST_WORKSHEET': 'Sheet1',
            'SERVICE_ACCOUNT_JSON': '{"type": "service_account"}'
        }
        
        mock_account = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.id = 'sheet123'
        mock_sheet.title = 'Test Sheet'
        mock_sheet.url = 'http://example.com'
        
        mock_creds.return_value = mock_account
        mock_account.open.return_value = mock_sheet
        mock_load.return_value = {"connections": {}, "shared": []}
        
        # 2. Run
        init_GWorkSheet(env, 'TEST_WORKSHEET')
        
        # 3. Verify
        # Expected shares: user1, user2, user3
        expected_emails = ['user1@example.com', 'user2@example.com', 'user3@example.com']
        
        # Get all calls to sheet.share
        actual_calls = mock_sheet.share.call_args_list
        actual_emails = [call.args[0] for call in actual_calls]
        
        for email in expected_emails:
            assert email in actual_emails, f"Expected share with {email} but not found"
        
        assert len(actual_emails) == 3, f"Expected 3 shares, got {len(actual_emails)}"
        
    @patch('egi_okr.utils.init_google_credentials')
    @patch('egi_okr.utils._load_process_cache')
    @patch('egi_okr.utils._save_process_cache')
    def test_init_GWorkSheet_cache_prevents_duplicate_share(self, mock_save, mock_load, mock_creds):
        """
        Verify that if an email is already in the 'shared' cache, it's not shared again.
        """
        # 1. Setup
        env = {
            'GOOGLE_SHEET_NAME': 'Test Sheet',
            'GOOGLE_SHARE_EMAILS': 'user1@example.com',
            'TEST_WORKSHEET': 'Sheet1'
        }
        
        mock_account = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.id = 'sheet123'
        
        mock_creds.return_value = mock_account
        mock_account.open.return_value = mock_sheet
        
        # Pretend user1 was already shared in a previous worksheet init
        mock_load.return_value = {
            "connections": {}, 
            "shared": ["sheet123:user1@example.com"]
        }
        
        # 2. Run
        init_GWorkSheet(env, 'TEST_WORKSHEET')
        
        # 3. Verify
        assert mock_sheet.share.call_count == 0, "Should not share again if already in cache"
