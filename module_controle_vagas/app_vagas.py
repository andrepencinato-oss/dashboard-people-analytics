print("INICIANDO SCRIPT APP_VAGAS...", flush=True)
import os
import sys
import io
import json
import threading
import webbrowser
import math
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

print("Importing pandas...", flush=True)
import pandas as pd

print("Importing traceback...", flush=True)
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(os.path.dirname(BASE_DIR), 'core', 'token.json')
CREDS_PATH = os.path.join(os.path.dirname(BASE_DIR), 'core', 'credentials.json')
DATA_DIR = os.path.join(BASE_DIR, 'data')

core_dir = os.path.join(os.path.dirname(BASE_DIR), 'core')
root_dir = os.path.dirname(BASE_DIR)
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

print("Importing drive_sync...", flush=True)
import drive_sync

print("Importing google stuff...", flush=True)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.exceptions import RefreshError

print("All imports done!", flush=True)

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDS_PATH
    
    print(f'DEBUG: Tentando carregar token em: {TOKEN_PATH}', flush=True)
    if not os.path.exists(TOKEN_PATH):
        print(f"[AUTH ERROR] Token nao encontrado no caminho absoluto: {TOKEN_PATH}", flush=True)

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            fallback_creds = TOKEN_PATH
            try:
                creds.refresh(Request())
            except RefreshError:
                if os.path.exists(fallback_creds):
                    os.remove(fallback_creds)
                
                if not os.path.exists(CREDS_PATH):
                    raise FileNotFoundError(f"Arquivo credentials.json não encontrado no caminho: {CREDS_PATH}")
                flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            if not os.path.exists(CREDS_PATH):
                raise FileNotFoundError(f"Arquivo credentials.json não encontrado no caminho: {CREDS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    return service

def sync_vagas_files():
    folder_id = '1R-DWrbqlocRx09BXF9s6KQbX0S9Es2Y0'
    service = get_drive_service()
    
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=10,
        fields="files(id, name)"
    ).execute()
    
    items = results.get('files', [])
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    downloaded = {}
    for item in items:
        file_id = item['id']
        file_name = item['name']
        
        name_lower = file_name.lower()
        
        # Skip the instruction document to prevent API crash (Google Docs cannot be downloaded directly via get_media)
        if 'passo a passo' in name_lower:
            continue
            
        request = service.files().get_media(fileId=file_id)
        file_path = os.path.join(DATA_DIR, file_name)
        
        try:
            fh = io.FileIO(file_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.close()
        except Exception as e:
            print(f"[SYNC WARNING] Failed to download {file_name}: {e}")
            continue
        
        if 'consolidad' in name_lower or 'colaboradores' in name_lower:
            downloaded['cons'] = file_path
        elif 'afastamento' in name_lower:
            downloaded['afas'] = file_path
        elif 'aviso' in name_lower:
            downloaded['aviso'] = file_path
            
    return downloaded

def parse_excel_to_2d_array(file_path):
    df = pd.read_excel(file_path, header=None, engine='xlrd')
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%d/%m/%Y')
            
    data = df.values.tolist()
    for i in range(len(data)):
        for j in range(len(data[i])):
            val = data[i][j]
            if pd.isna(val):
                data[i][j] = ''
            elif isinstance(val, float):
                if val.is_integer():
                    data[i][j] = int(val)
                elif math.isnan(val):
                    data[i][j] = ''
            elif isinstance(val, pd.Timestamp):
                data[i][j] = val.strftime('%d/%m/%Y')
    return data

class VagasHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html_path = os.path.join(BASE_DIR, 'dashboard_headcount.html')
                with open(html_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
                    
            elif self.path == '/api/sync-vagas':
                print("\n[API] Recebida requisicao em /api/sync-vagas", flush=True)
                try:
                    print("[API] Iniciando sincronizacao e autenticacao do Drive...", flush=True)
                    folder_id = '1R-DWrbqlocRx09BXF9s6KQbX0S9Es2Y0'
                    print(f"[DEBUG] Autenticando e listando arquivos na pasta ID {folder_id}...", flush=True)
                    service = get_drive_service()
                    
                    debug_results = service.files().list(q=f"'{folder_id}' in parents and trashed = false", fields="files(id, name)").execute()
                    debug_items = debug_results.get('files', [])
                    print(f"[DEBUG] Encontrados {len(debug_items)} arquivos na pasta:", flush=True)
                    for i in debug_items:
                        print(f"   - {i['name']} (ID: {i['id']})", flush=True)

                    files = sync_vagas_files()
                    
                    print(f"[API] Arquivos baixados: {list(files.keys())}", flush=True)
                    if 'cons' not in files or 'afas' not in files or 'aviso' not in files:
                        raise Exception(f"Arquivos obrigatorios nao encontrados. Encontrados: {list(files.keys())}")
                        
                    print("[API] Convertendo planilhas para JSON...", flush=True)
                    response_data = {
                        'cons': parse_excel_to_2d_array(files['cons']),
                        'afas': parse_excel_to_2d_array(files['afas']),
                        'aviso': parse_excel_to_2d_array(files['aviso'])
                    }
                    
                    print("[API] Conversao concluida com sucesso. Enviando resposta 200 OK.", flush=True)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                except Exception as e:
                    print(f"[API] Erro ocorrido: {str(e)}", flush=True)
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    err = {"status": "error", "message": str(e), "traceback": traceback.format_exc()}
                    self.wfile.write(json.dumps(err).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as global_e:
            print(f"\n[CRITICAL ERROR in do_GET]: {str(global_e)}", flush=True)
            print(traceback.format_exc(), flush=True)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            err = {"status": "error", "message": str(global_e), "traceback": traceback.format_exc()}
            self.wfile.write(json.dumps(err).encode('utf-8'))

def main():
    print("Entered main()", flush=True)
    
    print("Verificando autenticacao do Google Drive...", flush=True)
    try:
        get_drive_service()
        print("Autenticacao verificada com sucesso!", flush=True)
    except Exception as e:
        print(f"Erro na autenticação: {e}", flush=True)

    port = 5004
    server_address = ('127.0.0.1', port)
    print("Creating HTTPServer...", flush=True)
    httpd = HTTPServer(server_address, VagasHandler)
    print("HTTPServer created!", flush=True)
    
    url = f"http://127.0.0.1:{port}"
    print(f"Controle de Vagas iniciado em {url}", flush=True)
    
    def open_browser():
        try:
            os.startfile(url)
        except Exception:
            import subprocess
            subprocess.Popen(['start', url], shell=True)
            
    threading.Timer(1.5, open_browser).start()
    
    print("Servidor executando (bloqueando thread principal para diagnostico)...", flush=True)
    httpd.serve_forever()
    
    import time
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
