import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def main():
    creds = Credentials.from_authorized_user_file('token.json')
    service = build('drive', 'v3', credentials=creds)
    folder_id = '1A5Ap8NQAMyPRSQBW6OceQ2nUbvRDcq2p'
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    print("Files in update folder:", results.get('files', []))

if __name__ == '__main__':
    main()
