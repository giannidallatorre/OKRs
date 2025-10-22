import gspread
from oauth2client.service_account import ServiceAccountCredentials

def init_GWorkSheet(env):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(env['SERVICE_ACCOUNT_FILE'], scope)
        client = gspread.authorize(creds)
        sheet = client.open(env['GOOGLE_SHEET_NAME']).worksheet(env['GOOGLE_HTC_WORKSHEET'])
        return sheet
    except KeyError as e:
        raise KeyError(f"Missing required environment variable: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Service account file not found: {env['SERVICE_ACCOUNT_FILE']}")
    except gspread.SpreadsheetNotFound:
        raise gspread.SpreadsheetNotFound(f"Spreadsheet not found: {env['GOOGLE_SHEET_NAME']}")
    except gspread.WorksheetNotFound:
        raise gspread.WorksheetNotFound(f"Worksheet not found: {env['GOOGLE_HTC_WORKSHEET']}")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")