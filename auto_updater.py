import os
import sys
import json
import subprocess
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

UPDATE_FOLDER_ID = '1A5Ap8NQAMyPRSQBW6OceQ2nUbvRDcq2p'

def _parse_version(version_str):
    version_str = version_str.lower().replace('v', '').strip()
    parts = version_str.split('.')
    try:
        return tuple(map(int, parts))
    except ValueError:
        return (0, 0, 0)

def get_working_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

def check_and_apply_updates(current_version):
    """
    Verifica se há versão mais recente no Google Drive e aplica o update se existir.
    """
    print(f"Verificando atualizações. Versão atual: {current_version}...")
    try:
        working_dir = get_working_dir()
        token_path = os.path.join(working_dir, 'token.json')
        
        if not os.path.exists(token_path):
            print("Token não encontrado, impossível verificar atualizações.")
            return False
            
        creds = Credentials.from_authorized_user_file(token_path)
        service = build('drive', 'v3', credentials=creds)
        
        query = f"'{UPDATE_FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        version_file_id = None
        app_file_id = None
        
        for f in files:
            if f['name'] == 'version.json':
                version_file_id = f['id']
            elif f['name'] == 'app_desktop.exe':
                app_file_id = f['id']
                
        if not version_file_id or not app_file_id:
            print("Arquivos de atualização não encontrados no Drive.")
            return False
            
        # Download version.json
        request = service.files().get_media(fileId=version_file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        version_data = json.loads(fh.getvalue().decode('utf-8'))
        latest_version = version_data.get('version', '')
        
        current_tuple = _parse_version(current_version)
        latest_tuple = _parse_version(latest_version)
        
        print(f"Versão no Drive: {latest_version}")
        
        if latest_tuple > current_tuple:
            print("Atualização disponível! Preparando download...")
            
            new_exe_path = os.path.join(working_dir, "app_desktop_update.exe")
            if os.path.exists(new_exe_path):
                os.remove(new_exe_path)
                
            # Download new executable
            print("Baixando nova versão do Drive...")
            request = service.files().get_media(fileId=app_file_id)
            fh = io.FileIO(new_exe_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
            print("Download concluído. Reiniciando para aplicar a atualização...")
            
            bat_path = os.path.join(working_dir, "apply_update.bat")
            bat_content = f"""@echo off
echo Atualizando o sistema... Por favor aguarde.
timeout /t 3 /nobreak > nul
move /y "{new_exe_path}" "app_desktop.exe"
start app_desktop.exe
del "%~f0"
"""
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
                
            subprocess.Popen([bat_path], cwd=working_dir, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)
        else:
            print("O sistema já está na versão mais recente.")
            return False
            
    except Exception as e:
        print(f"Falha ao verificar/aplicar atualizações via Drive: {e}")
    
    return False

if __name__ == "__main__":
    check_and_apply_updates("v1.0.0")
