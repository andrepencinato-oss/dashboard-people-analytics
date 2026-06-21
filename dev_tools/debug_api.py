import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import googleapiclient.errors

def test():
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    token_path = 'token.json'
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    except Exception as e:
        print("Could not load token.json:", str(e))
        return
        
    service = build('drive', 'v3', credentials=creds)
    folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'
    
    query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and name contains '.xls' and trashed = false"
    
    try:
        results = service.files().list(
            q=query,
            orderBy="createdTime desc",
            pageSize=1,
            fields="files(id, name)"
        ).execute()
        print("Success!", results)
    except googleapiclient.errors.HttpError as e:
        print("HTTP ERROR DETAILS:")
        print(f"Status Code: {e.resp.status}")
        print(f"Error Content: {e.content.decode('utf-8')}")

if __name__ == '__main__':
    test()
