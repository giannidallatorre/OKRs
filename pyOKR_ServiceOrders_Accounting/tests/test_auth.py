import json
import os
import pytest
from google.oauth2 import service_account
from googleapiclient.discovery import build  # Added import for building API clients
from google.auth.exceptions import DefaultCredentialsError

def test_service_account_auth():
    """Test that the service account can authenticate and access Google Sheets."""
    
    # --- CONFIGURATION ---
    config_path = os.path.join('.config', 'service_account.json')
    # NOTE: Replace with the ID of a test sheet the SA has access to
    TEST_SHEET_ID = "YOUR_VALID_TEST_SHEET_ID" 
    
    assert os.path.exists(config_path), "Service account file not found"
    
    with open(config_path) as f:
        creds_data = json.load(f)
    
    # Define required scopes
    required_scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly'
    ]
    
    try:
        # 1. Create credentials object
        credentials = service_account.Credentials.from_service_account_info(
            creds_data, 
            scopes=required_scopes
        )
        
        # 2. REAL API TEST: Build service client
        sheets_service = build('sheets', 'v4', credentials=credentials)
        
        # 3. Perform a minimal API call (verifies authentication and permission)
        sheets_service.spreadsheets().get(
            spreadsheetId=TEST_SHEET_ID, 
            fields='properties/title'
        ).execute()
        
    except Exception as e:
        # Fails the test if authentication or API call fails
        pytest.fail(f"Authentication/Authorization Failed: {type(e).__name__}: {str(e)}")