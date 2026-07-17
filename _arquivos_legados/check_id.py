import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
creds = Credentials.from_authorized_user_file('token.json', SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'
query = f"'{folder_id}' in parents and name contains 'Extrato' and trashed = false"
results = drive_service.files().list(q=query, fields="files(id, name)", orderBy="createdTime desc", pageSize=1).execute()
items = results.get('files', [])
if items:
    print(f"I updated: {items[0]['id']} with name {items[0]['name']}")
else:
    print("No file found")
