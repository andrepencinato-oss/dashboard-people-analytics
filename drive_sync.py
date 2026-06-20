import os
import sys
import tempfile
import io
import traceback
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_working_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

def fetch_latest_excel():
    try:
        folder_id = '1ufta5I1ooBkXw1fqXx7fg64RG4D4MBtn'
        working_dir = get_working_dir()
        creds_path = os.path.join(working_dir, 'credentials.json')
        token_path = os.path.join(working_dir, 'token.json')
        
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(f"Arquivo credentials.json não encontrado no caminho: {creds_path}")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        service = build('drive', 'v3', credentials=creds)

        query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and name contains 'Extrato' and name contains '.xls' and trashed = false"
        results = service.files().list(
            q=query,
            orderBy="createdTime desc",
            pageSize=1,
            fields="files(id, name)"
        ).execute()

        items = results.get('files', [])
        if not items:
            raise Exception(f"A pasta '{folder_id}' está vazia ou não contém arquivos .xls.")
        
        file_id = items[0]['id']
        file_name = items[0]['name']

        request = service.files().get_media(fileId=file_id)
        
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file_name)
        
        fh = io.FileIO(file_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        fh.close()
        
        return file_path

    except Exception as e:
        error_details = traceback.format_exc()
        raise Exception(f"Falha ao sincronizar com Google Drive:\n{error_details}")
