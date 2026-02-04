
import unittest
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

if __name__ == '__main__':
    unittest.main()
