import os
import json
import hashlib
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

DRIVE_FOLDER_ID = '11G8qWpSj87bRo0EmK-JJCFqGQ82MLyRc'
LOCAL_PATH = 'core/acesso_config.json'
CLOUD_FILENAME = 'acesso_config_cloud.json'

def get_drive_service():
    creds_path = 'core/credentials.json'
    token_path = 'core/token_upload.json'
    if not os.path.exists(token_path):
        token_path = 'core/token.json'
        
    creds = Credentials.from_authorized_user_file(token_path)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def main():
    if not os.path.exists(LOCAL_PATH):
        print(f"File {LOCAL_PATH} not found.")
        data = {
            "usuarios": [
                {
                    "login": "Andre",
                    "senha": "*Savoia10",
                    "nome": "Administrador",
                    "setores": [],
                    "admin": True,
                    "ativo": True
                }
            ]
        }
    else:
        with open(LOCAL_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

    # Aplica HASH
    for u in data.get('usuarios', []):
        senha = u.get('senha', '')
        if not senha.startswith('sha256$'):
            u['senha'] = 'sha256$' + hashlib.sha256(senha.encode('utf-8')).hexdigest()

    temp_path = 'core/temp_acesso_config_cloud.json'
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    service = get_drive_service()

    # Verifica se já existe no drive
    query = f"name='{CLOUD_FILENAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])

    media = MediaFileUpload(temp_path, mimetype='application/json')
    if items:
        file_id = items[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
        print(f"File updated. ID: {file_id}")
    else:
        file_metadata = {
            'name': CLOUD_FILENAME,
            'parents': [DRIVE_FOLDER_ID]
        }
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File created. ID: {file.get('id')}")

if __name__ == '__main__':
    main()
