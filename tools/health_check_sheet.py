#!/usr/bin/env python3
import os
import sys

# Ensure src is in python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from egi_okr.utils import init_GWorkSheet, get_env_settings, colourise
    import datetime

    print("Starting Health Check...")
    
    # Mock environment for health check
    env = get_env_settings()
    env['GOOGLE_SHEET_NAME'] = "EGI_OKR_Test_Verify"
    env['GOOGLE_CLOUD_WORKSHEET'] = "Cloud"
    env['SERVICE_ACCOUNT_FILE'] = ".config/service_account.json"
    
    print(f"Connecting to worksheet: {env['GOOGLE_CLOUD_WORKSHEET']} in {env['GOOGLE_SHEET_NAME']}...")
    
    worksheet = init_GWorkSheet(env, 'GOOGLE_CLOUD_WORKSHEET')
    
    if worksheet:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("Connected successfully!")
        
        # Verify writing
        print("Writing verification message to A2...")
        worksheet.update([[ f"Verified at {timestamp}" ]], 'A2')
        
        print(colourise("green", "\nHEALTH CHECK PASSED!"))
        print(f"Checkout the sheet at: https://docs.google.com/spreadsheets/d/{worksheet.spreadsheet.id}")
    else:
        print(colourise("red", "\nHEALTH CHECK FAILED: Worksheet not found."))
        sys.exit(1)

except Exception as e:
    print(colourise("red", f"\nHEALTH CHECK FAILED: {e}"))
    import traceback
    traceback.print_exc()
    sys.exit(1)
