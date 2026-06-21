import os
import sys
import json
import subprocess
import re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

UPDATE_FOLDER_ID = '1A5Ap8NQAMyPRSQBW6OceQ2nUbvRDcq2p'

def update_version_files(new_version):
    print(f"Atualizando controladores de versão para {new_version}...")
    
    # 1. Atualiza app_desktop.py
    app_py = 'app_desktop.py'
    with open(app_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(r'APP_VERSION\s*=\s*".*?"', f'APP_VERSION = "{new_version}"', content)
    with open(app_py, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    # 2. Cria/Atualiza version.json local
    with open('version.json', 'w', encoding='utf-8') as f:
        json.dump({"version": new_version}, f)
        
    print("Versões atualizadas localmente.")

def run_pyinstaller():
    print("Executando PyInstaller (pode demorar um pouco)...")
    result = subprocess.run([sys.executable, '-m', 'PyInstaller', 'app_desktop.spec', '--clean', '-y'], capture_output=True, text=True)
    if result.returncode != 0:
        print("Erro no PyInstaller:")
        print(result.stderr)
        sys.exit(1)
    print("Executável gerado com sucesso na pasta 'dist/'.")

def upload_to_drive():
    print("Iniciando upload para o Google Drive...")
    creds = Credentials.from_authorized_user_file('token.json')
    service = build('drive', 'v3', credentials=creds)
    
    # Lista arquivos existentes na pasta
    query = f"'{UPDATE_FOLDER_ID}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    existing = {f['name']: f['id'] for f in files}
    
    files_to_upload = [
        ('version.json', 'application/json'),
        ('dist/app_desktop.exe', 'application/vnd.microsoft.portable-executable')
    ]
    
    for local_path, mimetype in files_to_upload:
        filename = os.path.basename(local_path)
        if not os.path.exists(local_path):
            print(f"Arquivo não encontrado: {local_path}")
            continue
            
        is_resumable = filename.endswith('.exe')
        media = MediaFileUpload(local_path, mimetype=mimetype, resumable=is_resumable)
        
        if filename in existing:
            print(f"Atualizando arquivo existente '{filename}' no Drive...")
            request = service.files().update(fileId=existing[filename], media_body=media)
        else:
            print(f"Criando novo arquivo '{filename}' no Drive...")
            file_metadata = {
                'name': filename,
                'parents': [UPDATE_FOLDER_ID]
            }
            request = service.files().create(body=file_metadata, media_body=media)
            
        if is_resumable:
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%.")
        else:
            request.execute()


            
    print("Upload concluído com sucesso!")

def main():
    if len(sys.argv) < 2:
        print("Uso: python deploy_manager.py <nova_versao> (ex: python deploy_manager.py v2.1.0)")
        sys.exit(1)
        
    new_version = sys.argv[1]
    update_version_files(new_version)
    run_pyinstaller()
    upload_to_drive()
    print("=== DEPLOY TOTALMENTE AUTÔNOMO CONCLUÍDO ===")

if __name__ == '__main__':
    main()
