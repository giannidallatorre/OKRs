#!/usr/bin/env python3
import gspread
import json
import sys
import os

def main():
    try:
        # Load credentials
        sa_file = '.config/service_account.json'
        if not os.path.exists(sa_file):
            print(f"Error: {sa_file} not found.")
            sys.exit(1)
            
        print("Authenticating with Google Sheets...")
        gc = gspread.service_account(filename=sa_file)
        
        sheet_name = "EGI_OKR_Test_Verify"
        print(f"Opening/Creating Sheet: {sheet_name}")
        
        try:
            sh = gc.open(sheet_name)
            print(f"Sheet '{sheet_name}' already exists.")
        except gspread.SpreadsheetNotFound:
            print("Creating new sheet...")
            sh = gc.create(sheet_name)
            
        print(f"Sheet URL: {sh.url}")
        print(f"Sheet ID: {sh.id}")

        # Share if email provided
        if len(sys.argv) > 1:
            email = sys.argv[1]
            print(f"Sharing sheet with {email}...")
            sh.share(email, perm_type='user', role='writer')
            print("Shared successfully.")
        else:
            print("\nNOTE: To share this sheet with your email, run:")
            print(f"python tools/create_test_sheet.py your-email@example.com")
        
        # Ensure Worksheets
        required_worksheets = [
            'Cloud', 'HTC', 'VOs', 'Report', 'Orders', 'SLAs',
            'CloudReport', 'HTCReport', 'OLAs'
        ]
        
        existing_titles = [ws.title for ws in sh.worksheets()]
        
        for req in required_worksheets:
            if req not in existing_titles:
                print(f"Creating worksheet: {req}")
                sh.add_worksheet(title=req, rows=100, cols=20)
                # Initialize headers?
                # For now just create. Modules usually verify headers or insert if missing.
                # Actually modules invoke 'check headers' but rely on 'Period' often.
                # Let's add simple header "Period" to Col 1 just in case.
                ws = sh.worksheet(req)
                ws.update([[ 'Period' ]], 'A1')
            else:
                print(f"Worksheet '{req}' exists.")
                
        print("\nSUCCESS: Test Sheet Ready.")
        print("\nPlease update your .env with:")
        print(f"GOOGLE_SHEET_NAME={sheet_name}")
        print("GOOGLE_CLOUD_WORKSHEET=Cloud")
        print("GOOGLE_HTC_WORKSHEET=HTC")
        print("GOOGLE_VOS_WORKSHEET=VOs")
        print("GOOGLE_VOS_REPORT_WORKSHEET=Report")
        print("GOOGLE_ORDERS_WORKSHEET=Orders")
        print("GOOGLE_SLAs_WORKSHEET=SLAs")
        print("GOOGLE_SLAs_CLOUD_WORKSHEET=CloudReport")
        print("GOOGLE_SLAs_HTC_WORKSHEET=HTCReport")
        print("GOOGLE_OLAs_WORKSHEET=OLAs")
        
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
