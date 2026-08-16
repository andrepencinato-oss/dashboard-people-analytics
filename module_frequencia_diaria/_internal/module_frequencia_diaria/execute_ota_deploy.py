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

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)

OTA_FOLDER_ID = "16iPgRhOPqb4pBDGI9FoBqQdYgnzuAcqg"
NEW_VERSION = "1.0.8"

def get_drive_service():
    token_path = os.path.join(PROJECT_ROOT, 'core', 'token.json')
    if not os.path.exists(token_path):
        token_path = os.path.join(MODULE_DIR, 'core', 'token.json')
    
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
            raise Exception("Token OAuth inválido ou indisponível em core/token.json")
            
    return build('drive', 'v3', credentials=creds)

def upload_or_update(service, folder_id, file_path, name, mimetype):
    query = f"'{folder_id}' in parents and name='{name}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
    if items:
        file_id = items[0]['id']
        print(f"  [UPDATE] Atualizando '{name}' (ID: {file_id})...")
        service.files().update(fileId=file_id, media_body=media).execute()
        return file_id
    else:
        print(f"  [CREATE] Criando '{name}' no Drive...")
        file_metadata = {'name': name, 'parents': [folder_id]}
        res = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return res.get('id')

def build_app_zip(zip_path, app_name):
    dist_dir = os.path.join(MODULE_DIR, 'dist', app_name)
    if not os.path.exists(dist_dir):
        dist_dir = os.path.join(PROJECT_ROOT, 'dist', app_name)
    
    if not os.path.exists(dist_dir):
        print(f"[AVISO] Pasta dist para {app_name} não encontrada em {dist_dir}")
        return False
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_full = os.path.join(root, file)
                rel_path = os.path.relpath(file_full, dist_dir)
                zipf.write(file_full, rel_path)
    
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"  [ZIP] Empacotado {app_name}: {size_mb:.2f} MB")
    return True

def update_version_files():
    targets = [
        os.path.join(MODULE_DIR, 'version.json'),
        os.path.join(PROJECT_ROOT, 'core', 'version.json'),
        os.path.join(PROJECT_ROOT, 'core', 'version_FrequenciaDiaria.json'),
        os.path.join(PROJECT_ROOT, 'core', 'version_Absenteismo_plug.json'),
        os.path.join(MODULE_DIR, 'core', 'version_FrequenciaDiaria.json'),
        os.path.join(MODULE_DIR, 'core', 'version_Absenteismo_plug.json')
    ]
    
    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        with open(t, 'w', encoding='utf-8') as f:
            json.dump({"version": NEW_VERSION}, f, indent=2)
    print(f"  [VERSION] Todos os arquivos de versão atualizados para v{NEW_VERSION}")

def main():
    print(f"=== INICIANDO DEPLOY OTA PRODUCTION (v{NEW_VERSION}) ===")
    
    # 1. Atualizar versão local
    update_version_files()
    
    # 2. Obter serviço Drive API
    service = get_drive_service()
    print("  [DRIVE] Autenticação com token.json realizada com sucesso.")
    
    tmp_dir = tempfile.mkdtemp()
    try:
        # Upload de arquivos de versão
        ver_file_main = os.path.join(MODULE_DIR, 'version.json')
        upload_or_update(service, OTA_FOLDER_ID, ver_file_main, 'version.json', 'application/json')
        upload_or_update(service, OTA_FOLDER_ID, ver_file_main, 'version_FrequenciaDiaria.json', 'application/json')
        upload_or_update(service, OTA_FOLDER_ID, ver_file_main, 'version_Absenteismo_plug.json', 'application/json')
        
        # Upload do comprovante de prova QA
        proof_img = os.path.join(MODULE_DIR, 'comprovante_setores_ok.png')
        if os.path.exists(proof_img):
            upload_or_update(service, OTA_FOLDER_ID, proof_img, 'comprovante_setores_ok.png', 'image/png')
            print("  [PROOF] Upload do comprovante_setores_ok.png concluído.")

        # Upload de zips e exes
        for app in ["FrequenciaDiaria", "Absenteismo_plug"]:
            zip_dest = os.path.join(tmp_dir, f'update_{app}.zip')
            if build_app_zip(zip_dest, app):
                upload_or_update(service, OTA_FOLDER_ID, zip_dest, f'update_{app}.zip', 'application/zip')
                if app == "FrequenciaDiaria":
                    gen_zip = os.path.join(tmp_dir, 'update.zip')
                    shutil.copy2(zip_dest, gen_zip)
                    upload_or_update(service, OTA_FOLDER_ID, gen_zip, 'update.zip', 'application/zip')
            
            exe_src = os.path.join(MODULE_DIR, 'dist', app, f'{app}.exe')
            if os.path.exists(exe_src):
                upload_or_update(service, OTA_FOLDER_ID, exe_src, f'{app}.exe', 'application/octet-stream')
                print(f"  [EXE] Upload direto do binário {app}.exe concluído.")
                
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        
    print(f"\n===============================================================")
    print(f"Deploy OTA Concluído: Triplo Quadro enviado para a nuvem com sucesso")
    print(f"Versão: v{NEW_VERSION} | Drive ID: {OTA_FOLDER_ID}")
    print(f"===============================================================")

if __name__ == '__main__':
    main()
