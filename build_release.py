import os
import zipfile
import json
import sys
import tempfile
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_drive_service():
    creds_path = os.path.join('core', 'token.json')
    if not os.path.exists(creds_path):
        print("Erro: token.json nao encontrado.")
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(creds_path)
    return build('drive', 'v3', credentials=creds)

def build_zip(zip_path):
    print("Iniciando empacotamento...")
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    excludes_dirs = ['data', '__pycache__', '.git', '.update_temp']
    excludes_files = ['token.json', 'token_upload.json', 'credentials.json', 'build_release.py']
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in excludes_dirs and not d.startswith('.')]
            
            for file in files:
                if file in excludes_files or file.endswith('.pyc') or file.endswith('.zip') or file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_root)
                zipf.write(file_path, rel_path)
    print(f"Pacote zip criado em {zip_path}")

def upload_file_to_drive(service, folder_id, file_path, name, mimetype):
    print(f"Buscando arquivo existente '{name}' no Drive...")
    query = f"'{folder_id}' in parents and name='{name}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
    if items:
        file_id = items[0]['id']
        print(f"Atualizando arquivo existente (ID: {file_id})...")
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        print(f"Criando novo arquivo '{name}'...")
        file_metadata = {'name': name, 'parents': [folder_id]}
        service.files().create(body=file_metadata, media_body=media).execute()
    print(f"Upload de '{name}' concluido!")

def main():
    print("=== HOMEDOCK SUITE - OTA RELEASE BUILDER ===")
    
    ota_config_path = os.path.join('core', 'ota_config.json')
    if not os.path.exists(ota_config_path):
        print("Erro: ota_config.json nao encontrado.")
        sys.exit(1)
    
    with open(ota_config_path, 'r') as f:
        config = json.load(f)
        
    folder_id = config.get('ota_folder_id')
    if not folder_id:
        print("Erro: ota_folder_id nao configurado.")
        sys.exit(1)

    version_path = os.path.join('core', 'version.json')
    with open(version_path, 'r') as f:
        v_data = json.load(f)
    current_version = v_data.get('version', '1.0.0')
    print(f"Versao atual registrada: {current_version}")
    
    new_version = input("Digite a nova versao (ex: 2.0.5) ou Enter para manter: ").strip()
    if new_version and new_version != current_version:
        v_data['version'] = new_version
        with open(version_path, 'w') as f:
            json.dump(v_data, f)
        print(f"Versao atualizada para {new_version}.")
    else:
        new_version = current_version

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, 'update.zip')
    
    build_zip(zip_path)
    
    service = get_drive_service()
    
    print("\nFazendo upload para o Drive OTA...")
    upload_file_to_drive(service, folder_id, zip_path, 'update.zip', 'application/zip')
    upload_file_to_drive(service, folder_id, version_path, 'version.json', 'application/json')
    
    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
    os.rmdir(temp_dir)
    
    print("\n[SUCESSO] OTA Release publicada e pronta para download pelos launchers!")

if __name__ == '__main__':
    main()
