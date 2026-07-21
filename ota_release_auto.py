"""
Script OTA não-interativo para CI/CD — executa sem prompts.
Uso: py -3 ota_release_auto.py [versao]
"""
import os, sys, json, zipfile, tempfile
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def get_drive_service():
    creds_path = os.path.join('core', 'token.json')
    creds = Credentials.from_authorized_user_file(creds_path)
    return build('drive', 'v3', credentials=creds)

def build_zip(zip_path):
    excludes_dirs  = ['data', '__pycache__', '.git', '.update_temp', '.update_stage', 'build', 'dist']
    excludes_files = ['token.json', 'token_upload.json', 'token_deploy.json', 'token_old.json',
                      'credentials.json', 'apply_update.bat', 'ota_release_auto.py']
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in excludes_dirs and not d.startswith('.')]
            for file in files:
                if (file in excludes_files or file.endswith('.pyc')
                        or file.endswith('.zip') or file.startswith('.')
                        or file.endswith('.spec')):
                    continue
                file_path = os.path.join(root, file)
                rel_path  = os.path.relpath(file_path, PROJECT_ROOT)
                zipf.write(file_path, rel_path)
    print(f"ZIP criado: {zip_path}")

def upload(service, folder_id, file_path, name, mime):
    query   = f"'{folder_id}' in parents and name='{name}' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items   = results.get('files', [])
    media   = MediaFileUpload(file_path, mimetype=mime, resumable=True)
    if items:
        service.files().update(fileId=items[0]['id'], media_body=media).execute()
        print(f"Atualizado: {name}")
    else:
        service.files().create(body={'name': name, 'parents': [folder_id]},
                               media_body=media).execute()
        print(f"Criado: {name}")

def main():
    version_path    = os.path.join('core', 'version.json')
    ota_config_path = os.path.join('core', 'ota_config.json')

    with open(version_path) as f:
        v_data  = json.load(f)
    version = sys.argv[1] if len(sys.argv) > 1 else v_data.get('version', '1.0.0')
    v_data['version'] = version
    with open(version_path, 'w') as f:
        json.dump(v_data, f, indent=2)
    print(f"Versao: {version}")

    with open(ota_config_path) as f:
        config    = json.load(f)
    folder_id = config['ota_folder_id']

    tmp     = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, 'update.zip')
    build_zip(zip_path)

    service = get_drive_service()
    upload(service, folder_id, zip_path, 'update.zip',   'application/zip')
    upload(service, folder_id, version_path, 'version.json', 'application/json')

    os.remove(zip_path)
    print(f"\n[OK] OTA v{version} publicada no Drive!")

if __name__ == '__main__':
    main()
