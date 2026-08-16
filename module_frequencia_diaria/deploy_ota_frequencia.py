import os
import sys
import json
import zipfile
import tempfile
import shutil
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_drive_service(base_dir):
    token_path = os.path.join(base_dir, 'core', 'token.json')
    creds_path = os.path.join(base_dir, 'core', 'credentials.json')
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            print("[ERRO] Token OAuth ausente ou inválido.")
            sys.exit(1)
            
    return build('drive', 'v3', credentials=creds)

def upload_or_update(service, folder_id, file_path, name, mimetype):
    query = f"'{folder_id}' in parents and name='{name}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
    if items:
        file_id = items[0]['id']
        print(f"  -> Atualizando '{name}' existente no Drive (ID: {file_id})...")
        service.files().update(fileId=file_id, media_body=media).execute()
        return file_id
    else:
        print(f"  -> Criando novo arquivo '{name}' no Drive...")
        file_metadata = {'name': name, 'parents': [folder_id]}
        res = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return res.get('id')

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ota_config_path = os.path.join(base_dir, 'core', 'ota_config.json')
    version_path = os.path.join(base_dir, 'core', 'version_FrequenciaDiaria.json')
    
    with open(ota_config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    folder_id = config.get('ota_folder_id')
    if not folder_id:
        print("[ERRO] ota_folder_id nao configurado.")
        sys.exit(1)
        
    with open(version_path, 'r', encoding='utf-8') as f:
        v_data = json.load(f)
    version_str = v_data.get('version', '2.4.2')
    
    print(f"=== INICIANDO DEPLOY OTA FREQUENCIA DIARIA (v{version_str}) ===")
    
    # 1. Conectar ao Drive
    print("[1/3] Conectando ao Google Drive API...")
    service = get_drive_service(base_dir)
    print("      Conectado com sucesso.")
    
    # 2. Empacotar ZIP
    print("[2/3] Empacotando update_FrequenciaDiaria.zip...")
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, 'update_FrequenciaDiaria.zip')
    
    excludes_files = ['deploy_ota_frequencia.py', 'test_frequencia_exe_test.py', 'apply_update.bat']
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file in excludes_files or file.endswith('.pyc') or file.startswith('.'):
                    continue
                file_full = os.path.join(root, file)
                rel_path = os.path.relpath(file_full, base_dir)
                zipf.write(file_full, rel_path)
                
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"      ZIP gerado: {zip_size_mb:.2f} MB")
    
    # 3. Fazer Upload para o Drive
    print("[3/3] Enviando arquivos para a pasta OTA no Drive...")
    zip_id = upload_or_update(service, folder_id, zip_path, 'update_FrequenciaDiaria.zip', 'application/zip')
    ver_id = upload_or_update(service, folder_id, version_path, 'version_FrequenciaDiaria.json', 'application/json')
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    print("\n[RECIBO DE DEPLOY OTA CONCLUIDO]")
    print(f"  Versão Publicada: v{version_str}")
    print(f"  Drive Folder ID:  {folder_id}")
    print(f"  ZIP File ID:      {zip_id}")
    print(f"  Version File ID:  {ver_id}")
    print("===============================================================")

if __name__ == '__main__':
    main()
