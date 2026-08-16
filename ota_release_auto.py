import os, sys, json, zipfile, tempfile
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def get_drive_service():
    creds_path = os.path.join('core', 'token.json')
    creds = Credentials.from_authorized_user_file(creds_path)
    return build('drive', 'v3', credentials=creds)

def build_zip(zip_path, app_name):
    base_dir = os.path.join(PROJECT_ROOT, 'dist', app_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path  = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, rel_path)
    print(f"ZIP criado: {zip_path} (from {app_name})")

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
    service = get_drive_service()

    # Generic upload as fallback
    zip_path_gen = os.path.join(tmp, 'update.zip')
    if os.path.exists(os.path.join(PROJECT_ROOT, 'dist', 'FrequenciaDiaria')):
        build_zip(zip_path_gen, 'FrequenciaDiaria')
        upload(service, folder_id, zip_path_gen, 'update.zip',   'application/zip')
    upload(service, folder_id, version_path, 'version.json', 'application/json')

    # Specific uploads for all apps we support
    for specific_name in ["FrequenciaDiaria", "Absenteismo_plug"]:
        dist_dir = os.path.join(PROJECT_ROOT, 'dist', specific_name)
        if not os.path.exists(dist_dir):
            print(f"Aviso: dist/{specific_name} nao encontrado, pulando upload.")
            continue
            
        # Update core version files specific to this app
        v_file_path = os.path.join('core', f'version_{specific_name}.json')
        with open(v_file_path, 'w') as f:
            json.dump(v_data, f, indent=2)
            
        zip_path_spec = os.path.join(tmp, f'update_{specific_name}.zip')
        build_zip(zip_path_spec, specific_name)
        
        upload(service, folder_id, v_file_path, f'version_{specific_name}.json', 'application/json')
        upload(service, folder_id, zip_path_spec, f'update_{specific_name}.zip', 'application/zip')

    print(f"\n[OK] OTA v{version} publicada no Drive!")

if __name__ == '__main__':
    main()
