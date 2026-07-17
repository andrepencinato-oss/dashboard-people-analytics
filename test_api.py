import os
import sys
sys.path.insert(0, 'core')
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
creds = Credentials.from_authorized_user_file('core/token.json', SCOPES)
print('Valid:', creds.valid)
print('Expired:', creds.expired)

if creds.expired:
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    print('Refreshed Valid:', creds.valid)

service = build('drive', 'v3', credentials=creds)
results = service.files().list(q="'16iPgRhOPqb4pBDGI9FoBqQdYgnzuAcqg' in parents", pageSize=10).execute()
print(results.get('files', []))
