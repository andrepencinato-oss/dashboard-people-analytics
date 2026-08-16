import os
import sys
import tempfile
import io
import traceback
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SCOPES_UPLOAD = ['https://www.googleapis.com/auth/drive']

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'core')
    return os.path.abspath(os.path.dirname(__file__))

def get_working_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def fetch_latest_excel():
    try:
        folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'
        base_path = get_base_path()
        working_dir = get_working_dir()
        creds_path = os.path.join(base_path, 'credentials.json')
        token_path = os.path.join(working_dir, 'token.json')
        if not getattr(sys, 'frozen', False):
            token_path = os.path.join(working_dir, 'core', 'token.json')
        
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
        if not creds or not creds.valid:
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    raise Exception("Needs new authentication")
            except Exception:
                if not os.path.exists(creds_path):
                    fallback_creds = os.path.join(working_dir, 'credentials.json')
                    if os.path.exists(fallback_creds):
                        creds_path = fallback_creds
                    else:
                        raise FileNotFoundError(f"Arquivo credentials.json não encontrado no caminho: {creds_path}")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        service = build('drive', 'v3', credentials=creds)

        query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and name contains 'Extrato' and trashed = false"
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

def auto_upload_to_drive(file_path):
    try:
        folder_id = '1Ir3UO_W5w5fx76a-BmB0JVPP5vrCogZ_'
        base_path = get_base_path()
        working_dir = get_working_dir()
        creds_path = os.path.join(base_path, 'credentials.json')
        token_path = os.path.join(working_dir, 'token_upload.json')
        if not getattr(sys, 'frozen', False):
            token_path = os.path.join(working_dir, 'core', 'token_upload.json')
        
        if not os.path.exists(token_path):
            raise Exception("token_upload.json não encontrado. Autenticação manual prévia é necessária.")
            
        creds = Credentials.from_authorized_user_file(token_path, SCOPES_UPLOAD)
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            else:
                raise Exception("Token expirado sem refresh_token. Re-autenticação manual necessária.")

        service = build('drive', 'v3', credentials=creds)
        
        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Mimetype handling based on file extension
        mimetype = 'application/octet-stream'
        if file_name.lower().endswith('.csv'):
            mimetype = 'text/csv'
        elif file_name.lower().endswith('.xlsx') or file_name.lower().endswith('.xls'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif file_name.lower().endswith('.json'):
            mimetype = 'application/json'
            
        media = MediaFileUpload(file_path, mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Arquivo '{file_name}' enviado para o Drive com sucesso. ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Falha ao enviar para Google Drive:\n{error_details}")
        return None
