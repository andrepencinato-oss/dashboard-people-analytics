import drive_sync
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import os
import io

def download_files():
    folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'
    working_dir = drive_sync.get_working_dir()
    token_path = os.path.join(working_dir, 'token.json')
    creds = Credentials.from_authorized_user_file(token_path, drive_sync.SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and name contains '.xls' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    for item in items:
        file_id = item['id']
        file_name = item['name']
        print(f"Downloading {file_name}...")
        
        request = service.files().get_media(fileId=file_id)
        file_path = os.path.join(r"D:\Users\andre.WIN-UT7BSJO8U2I\Temp", file_name)
        
        fh = io.FileIO(file_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.close()
        print(f"Downloaded to {file_path}")

if __name__ == '__main__':
    download_files()
