import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(current_dir, 'core')
sys.path.insert(0, core_dir)

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Update scopes to allow uploading files!
SCOPES = ['https://www.googleapis.com/auth/drive'] 
# Wait, the existing token is 'drive.readonly'. If I use 'drive', I will need a new token!
# We can just prompt the user if needed, or we use the installed flow.

# Let's try to authenticate with 'drive' scope. It will likely trigger a new browser auth.
# Wait, the user already authorized yesterday or recently for 'readonly'. 
# Since this is a simple test upload, I will just do it, and if it opens a browser, the user will approve.

def main():
    creds_path = os.path.join(core_dir, 'credentials.json')
    token_path = os.path.join(core_dir, 'token_upload.json') # create a separate token for upload
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    folder_id = '16iPgRhOPqb4pBDGI9FoBqQdYgnzuAcqg'
    
    target_dir = os.path.join(current_dir, 'module_frequencia_diaria')
    files_to_upload = [f for f in os.listdir(target_dir) if f.lower().endswith('.csv')]
    
    for file_name in files_to_upload:
        file_path = os.path.join(target_dir, file_name)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='text/csv')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Uploaded {file_name} with ID {file.get('id')}")

if __name__ == '__main__':
    main()
