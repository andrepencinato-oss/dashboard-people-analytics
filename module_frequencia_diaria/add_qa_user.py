"""
Script para adicionar usuário QA diretamente ao Google Drive.
Usa um temp path alternativo para evitar o lock do arquivo.
"""
import sys, json, hashlib, os, io, tempfile
sys.path.insert(0, r'd:\Projeto geral\People analytics - GP\module_frequencia_diaria')
sys.path.insert(0, r'd:\Projeto geral\People analytics - GP\core')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

DRIVE_FOLDER_ID = '11G8qWpSj87bRo0EmK-JJCFqGQ82MLyRc'
CLOUD_FILENAME = 'acesso_config_cloud.json'

# Auth
core_dir = r'd:\Projeto geral\People analytics - GP\core'
token_path = os.path.join(core_dir, 'token.json')
creds = Credentials.from_authorized_user_file(token_path)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
service = build('drive', 'v3', credentials=creds)

# Download current config
query = f"name='{CLOUD_FILENAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
results = service.files().list(q=query, fields="files(id)").execute()
items = results.get('files', [])

if items:
    file_id = items[0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    config = json.loads(fh.read().decode('utf-8'))
else:
    config = {"usuarios": []}

print("Usuarios atuais:", [u['login'] for u in config.get('usuarios', [])])

# Remove QA user if exists
config['usuarios'] = [u for u in config['usuarios'] if u['login'] != 'QA_Gestor_Test']

# Add QA Gestor
senha_hash = 'sha256$' + hashlib.sha256('qa123'.encode('utf-8')).hexdigest()
config['usuarios'].append({
    'login': 'QA_Gestor_Test',
    'senha': senha_hash,
    'nome': 'QA Gestor Teste',
    'admin': False,
    'gestor': True,
    'setores': [],
    'ativo': True
})

# Upload using system temp dir (avoids lock)
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
    temp_path = f.name

media = MediaFileUpload(temp_path, mimetype='application/json')
if items:
    service.files().update(fileId=file_id, media_body=media).execute()
else:
    file_metadata = {'name': CLOUD_FILENAME, 'parents': [DRIVE_FOLDER_ID]}
    service.files().create(body=file_metadata, media_body=media).execute()

os.remove(temp_path)
print("QA_Gestor_Test adicionado com sucesso ao Drive!")
print("Usuarios agora:", [u['login'] for u in config['usuarios']])
