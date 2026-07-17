import os
from data_processor import get_credentials
from googleapiclient.discovery import build

creds = get_credentials()
service = build('drive', 'v3', credentials=creds)
results = service.files().list(q="name contains 'Absente' and trashed = false", fields="files(id, name, modifiedTime)").execute()
print("Files:", [(f['name'], f['modifiedTime']) for f in results.get('files', [])])
