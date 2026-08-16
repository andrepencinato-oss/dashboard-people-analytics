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
NEW_VERSION = "2.6.4"

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

def build_executables():
    import subprocess
    print("  [BUILD] Compilando executáveis com PyInstaller...")
    for spec_file in ["Absenteismo_plug.spec"]:
        spec_path = os.path.join(MODULE_DIR, spec_file)
        if os.path.exists(spec_path):
            print(f"    -> Compilando {spec_file}...")
            res = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", spec_path], cwd=MODULE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                print(f"    [ERRO] Falha ao compilar {spec_file}: {res.stderr[-300:]}")
            else:
                print(f"    -> {spec_file} compilado com sucesso.")
                
                # Pull out the launcher scripts from _internal to root so the user can easily click them
                app_name = spec_file.replace('.spec', '')
                internal_dir = os.path.join(MODULE_DIR, 'dist', app_name, '_internal')
                root_dir = os.path.join(MODULE_DIR, 'dist', app_name)
                for script in ["iniciar_servidor.vbs", "instalar_servico.bat"]:
                    src = os.path.join(internal_dir, script)
                    dst = os.path.join(root_dir, script)
                    if os.path.exists(src):
                        import shutil
                        shutil.copy2(src, dst)

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
        os.path.join(MODULE_DIR, 'core', 'version_Absenteismo_plug.json'),
        os.path.join(MODULE_DIR, 'dist', 'Absenteismo_plug', '_internal', 'core', 'version_Absenteismo_plug.json'),
        os.path.join(MODULE_DIR, 'dist', 'Absenteismo_plug', 'core', 'version_Absenteismo_plug.json'),
    ]
    
    for t in targets:
        if os.path.exists(os.path.dirname(t)):
            with open(t, 'w', encoding='utf-8') as f:
                json.dump({"version": NEW_VERSION}, f, indent=2)
    print(f"  [VERSION] Todos os arquivos de versão atualizados para v{NEW_VERSION}")

def main():
    print(f"=== INICIANDO DEPLOY OTA PRODUCTION (v{NEW_VERSION}) ===")
    
    # 1. Atualizar versão local
    update_version_files()
    
    # 2. Compilar binários limpos
    build_executables()

    # Re-atualizar arquivos de versão pós-compilação nas pastas dist
    update_version_files()
    
    # 3. Obter serviço Drive API
    service = get_drive_service()
    print("  [DRIVE] Autenticação com token.json realizada com sucesso.")
    
    tmp_dir = tempfile.mkdtemp()
    try:
        # Upload de arquivos de versão
        ver_file_main = os.path.join(MODULE_DIR, 'version.json')
        upload_or_update(service, OTA_FOLDER_ID, ver_file_main, 'version.json', 'application/json')
        upload_or_update(service, OTA_FOLDER_ID, ver_file_main, 'version_Absenteismo_plug.json', 'application/json')
        
        # Upload do comprovante de prova QA
        proof_img = os.path.join(MODULE_DIR, 'comprovante_setores_ok.png')
        if os.path.exists(proof_img):
            upload_or_update(service, OTA_FOLDER_ID, proof_img, 'comprovante_setores_ok.png', 'image/png')
            print("  [PROOF] Upload do comprovante_setores_ok.png concluído.")

        proof_hc = os.path.join(MODULE_DIR, 'print_historico_headcount_ok.png')
        if os.path.exists(proof_hc):
            upload_or_update(service, OTA_FOLDER_ID, proof_hc, 'print_historico_headcount_ok.png', 'image/png')
            print("  [PROOF] Upload do print_historico_headcount_ok.png concluído.")

        # Upload de zips e exes
        for app in ["Absenteismo_plug"]:
            zip_dest = os.path.join(tmp_dir, f'update_{app}.zip')
            if build_app_zip(zip_dest, app):
                upload_or_update(service, OTA_FOLDER_ID, zip_dest, f'update_{app}.zip', 'application/zip')
                
                # Copy zip back to dist so the user has it locally
                local_zip = os.path.join(MODULE_DIR, 'dist', f'{app}.zip')
                shutil.copy2(zip_dest, local_zip)
            
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
