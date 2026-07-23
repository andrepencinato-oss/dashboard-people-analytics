import os
import sys
import json
import zipfile
import subprocess
import tempfile
import shutil
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VERSION = "2.1.6"

def update_version_files():
    v_data = {"version": VERSION}
    for filename in ['version.json', 'version_FrequenciaDiaria.json']:
        filepath = os.path.join(PROJECT_ROOT, 'core', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(v_data, f, indent=2)
    print(f"[VERSION] Versao fixada em {VERSION}")

def get_drive_service():
    creds_path = os.path.join(PROJECT_ROOT, 'core', 'token.json')
    if not os.path.exists(creds_path):
        print("[ERROR] core/token.json nao encontrado.")
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(creds_path)
    return build('drive', 'v3', credentials=creds)

def compile_app():
    spec_path = os.path.join(PROJECT_ROOT, 'module_frequencia_diaria', 'FrequenciaDiaria.spec')
    print(f"\n[BUILD] Compilando FrequenciaDiaria via PyInstaller...")
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', spec_path]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("[BUILD] ERRO na compilacao com PyInstaller.")
        sys.exit(1)
    print("[BUILD] Compilacao concluida!")

def build_zip(zip_path, base_dir):
    print(f"[ZIP] Empacotando {base_dir} -> {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, rel_path)
    print(f"[ZIP] Pacote gerado com sucesso!")

def upload_file_to_drive(service, folder_id, file_path, name, mimetype):
    print(f"[DRIVE] Verificando se '{name}' ja existe no Drive...")
    query = f"'{folder_id}' in parents and name='{name}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
    if items:
        file_id = items[0]['id']
        print(f"[DRIVE] Atualizando arquivo existente ID: {file_id}...")
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        print(f"[DRIVE] Criando novo arquivo '{name}'...")
        file_metadata = {'name': name, 'parents': [folder_id]}
        service.files().create(body=file_metadata, media_body=media).execute()
    print(f"[DRIVE] Upload de '{name}' concluido!")

def run_git(args):
    result = subprocess.run(['git'] + args, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[GIT WARN] git {' '.join(args)} => {result.stderr.strip()}")
    else:
        print(f"[GIT] git {' '.join(args)} OK")
    return result.returncode == 0

def git_release():
    print(f"\n[GIT] Automatizando commit e tag no GitHub...")
    run_git(['add', '.'])
    commit_msg = f"Release v{VERSION} - Adicionar liberacao forçada de processos antigos no launcher"
    run_git(['commit', '-m', commit_msg])
    
    tag_name = f'v{VERSION}'
    run_git(['tag', '-f', '-a', tag_name, '-m', f'Release v{VERSION}'])
    
    push_ok = run_git(['push', 'origin', 'HEAD'])
    tag_ok = run_git(['push', 'origin', tag_name, '--force'])
    
    if push_ok and tag_ok:
        print(f"[GIT] Release {tag_name} publicada no GitHub!")
    else:
        print(f"[GIT] Tag e commits criados localmente.")

def main():
    print(f"=== RE-PUBLICANDO OTA V{VERSION} ===")
    update_version_files()
    
    ota_config_path = os.path.join(PROJECT_ROOT, 'core', 'ota_config.json')
    with open(ota_config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    folder_id = config['ota_folder_id']
    
    compile_app()
    
    dist_dir = os.path.join(PROJECT_ROOT, 'dist', 'FrequenciaDiaria')
    if not os.path.exists(dist_dir):
        print(f"[ERROR] Pasta {dist_dir} nao existe.")
        sys.exit(1)
        
    temp_dir = tempfile.mkdtemp()
    zip_freq = os.path.join(temp_dir, 'update_FrequenciaDiaria.zip')
    zip_gen = os.path.join(temp_dir, 'update.zip')
    
    build_zip(zip_freq, dist_dir)
    shutil.copy(zip_freq, zip_gen)
    
    service = get_drive_service()
    
    v_freq_path = os.path.join(PROJECT_ROOT, 'core', 'version_FrequenciaDiaria.json')
    v_gen_path = os.path.join(PROJECT_ROOT, 'core', 'version.json')
    
    upload_file_to_drive(service, folder_id, zip_freq, 'update_FrequenciaDiaria.zip', 'application/zip')
    upload_file_to_drive(service, folder_id, v_freq_path, 'version_FrequenciaDiaria.json', 'application/json')
    
    upload_file_to_drive(service, folder_id, zip_gen, 'update.zip', 'application/zip')
    upload_file_to_drive(service, folder_id, v_gen_path, 'version.json', 'application/json')
    
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    git_release()
    
    print(f"\n[SUCESSO] OTA Release v{VERSION} atualizada com kill-process logic!")

if __name__ == '__main__':
    main()
