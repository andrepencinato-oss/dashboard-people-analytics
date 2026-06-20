import drive_sync
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os

def list_files():
    folder_id = '1ufta5I1ooBkXw1fqXx7fg64RG4D4MBtn'
    working_dir = drive_sync.get_working_dir()
    token_path = os.path.join(working_dir, 'token.json')
    creds = Credentials.from_authorized_user_file(token_path, drive_sync.SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])
    
    print(f"Files in folder {folder_id}:")
    for item in items:
        print(f"{item['name']} ({item['mimeType']})")

if __name__ == '__main__':
    list_files()
