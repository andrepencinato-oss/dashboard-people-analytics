import os
import sys
import json
import io
import zipfile
import shutil
import urllib.request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def get_drive_service():
    import sys
    
    # 1. Busca no LOCALAPPDATA onde o app_frequencia.py salva
    core_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PeopleAnalytics', 'core')
    creds_path = os.path.join(core_data_dir, 'token.json')
    
    # 2. Fallbacks de localizacao caso o LOCALAPPDATA ainda nao tenha sido populado
    if not os.path.exists(creds_path):
        if getattr(sys, 'frozen', False):
            creds_path = os.path.join(sys._MEIPASS, 'core', 'token.json')
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creds_path = os.path.join(base_dir, 'core', 'token.json')

    if not os.path.exists(creds_path):
        return None
    creds = Credentials.from_authorized_user_file(creds_path)
    return build('drive', 'v3', credentials=creds)

def check_and_download_update():
    """
    Checa se ha atualizacoes no Drive.
    Retorna True se baixou uma atualizacao e ela esta pronta para aplicacao na pasta .update_stage
    """
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        app_root = os.path.dirname(sys.executable)
        app_name = os.path.basename(sys.executable).replace('.exe', '')
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_root = base_dir
        app_name = "source"

    ota_config_path = os.path.join(base_dir, 'core', 'ota_config.json')
    version_path = os.path.join(base_dir, 'core', f'version_{app_name}.json')
    
    # Fallback para o arquivo genérico caso o específico não exista localmente ainda
    if not os.path.exists(version_path):
        fallback_path = os.path.join(base_dir, 'core', 'version.json')
        if os.path.exists(fallback_path):
            version_path = fallback_path
    
    if not os.path.exists(ota_config_path):
        return False
        
    with open(ota_config_path, 'r') as f:
        config = json.load(f)
        
    folder_id = config.get('ota_folder_id')
    if not folder_id:
        return False
        
    current_version = "1.0.0"
    if os.path.exists(version_path):
        with open(version_path, 'r') as f:
            v_data = json.load(f)
            current_version = v_data.get('version', '1.0.0')

    service = get_drive_service()
    if not service:
        return False

    # Checar version_{app_name}.json no drive
    query = f"'{folder_id}' in parents and name='version_{app_name}.json' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        return False
        
    version_file_id = items[0]['id']
    request = service.files().get_media(fileId=version_file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        
    fh.seek(0)
    try:
        remote_v_data = json.loads(fh.read().decode('utf-8'))
        remote_version = remote_v_data.get('version')
    except:
        return False

    def parse_version(v_str):
        try:
            return tuple(map(int, v_str.strip().split('.')))
        except Exception:
            return (0, 0, 0)

    if remote_version and parse_version(remote_version) > parse_version(current_version):
        print(f"\n[OTA UPDATE] Nova versao detectada: {remote_version} (Atual: {current_version})")
        print("[OTA UPDATE] Iniciando download silencioso...")
        
        query = f"'{folder_id}' in parents and name='update_{app_name}.zip' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if not items:
            print(f"[OTA UPDATE] Arquivo update_{app_name}.zip nao encontrado no Drive. Abortando update.")
            return False
            
        zip_file_id = items[0]['id']
        
        update_dir = os.path.join(app_root, '.update_stage')
        if os.path.exists(update_dir):
            shutil.rmtree(update_dir)
        os.makedirs(update_dir, exist_ok=True)
        
        zip_path = os.path.join(update_dir, 'update.zip')
        request = service.files().get_media(fileId=zip_file_id)
        fh = io.FileIO(zip_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.close()
        
        print("[OTA UPDATE] Download concluido. Descompactando...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(update_dir)
            
        os.remove(zip_path)
        print("[OTA UPDATE] Arquivos estagiados com sucesso. Pronto para aplicacao.")
        return True

    return False
