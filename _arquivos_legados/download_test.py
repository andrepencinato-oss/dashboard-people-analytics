import io
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'

creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('drive', 'v3', credentials=creds)

query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and name contains 'Extrato' and trashed = false"
results = service.files().list(q=query, fields="files(id, name)", orderBy="createdTime desc", pageSize=1).execute()
items = results.get('files', [])

file_id = items[0]['id']
file_name = items[0]['name']

request = service.files().get_media(fileId=file_id)
fh = io.FileIO(file_name, mode='wb')
downloader = MediaIoBaseDownload(fh, request)
done = False
while not done:
    status, done = downloader.next_chunk()

print(f"Downloaded {file_name}")
