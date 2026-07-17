import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

def main():
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    sheets_service = build('sheets', 'v4', credentials=creds)

    spreadsheet_id = '1_ohJciOqOJWzeBc_NAEb7vion-pBS65T'
    
    # Try to read row 700 to verify
    range_name = 'A690:A710'  # Check around 700
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        rows = result.get('values', [])
        print(f"Values around A700: {rows}")
        
        # Write "eu estou aqui" to A700
        body = {
            'values': [['eu estou aqui']]
        }
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A700',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print("Successfully updated cell A700 in Sheets!")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
