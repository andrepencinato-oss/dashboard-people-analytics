import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'

creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('drive', 'v3', credentials=creds)

query = f"'{folder_id}' in parents and trashed = false"
results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
print(results.get('files', []))
