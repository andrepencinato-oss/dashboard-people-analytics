import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'

creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('drive', 'v3', credentials=creds)

query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and name contains 'Extrato' and name contains '.xls' and trashed = false"
results = service.files().list(q=query, fields="files(id, name, mimeType)", orderBy="createdTime desc", pageSize=1).execute()
print("Query result:")
print(results.get('files', []))
