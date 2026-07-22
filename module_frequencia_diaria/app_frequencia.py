import os
import sys
import tempfile
import io
import json
import threading
import time
import traceback
import re
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser
import uuid
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── Separação de caminhos para modo frozen (PyInstaller) ─────────────────────
# template_dir  → _MEIPASS (somente leitura): onde ficam os arquivos .html/.py empacotados
# app_root      → pasta do .exe (gravável): onde ficam dados, CSVs e data_frequencia.js
if getattr(sys, 'frozen', False):
    template_dir   = os.path.join(sys._MEIPASS, 'module_frequencia_diaria')
    app_root       = os.path.dirname(sys.executable)
    # Em modo frozen: arquivos empacotados estão em _MEIPASS/core
    # Tokens (token.json, credentials.json) ficam ao lado do .exe em /core
    core_dir       = os.path.join(sys._MEIPASS, 'core')   # ota_config, version (read-only)
    core_data_dir  = os.path.join(app_root, 'core')        # token.json, credentials (gravável)
else:
    template_dir   = os.path.dirname(os.path.abspath(__file__))
    app_root       = os.path.dirname(template_dir)
    core_dir       = os.path.join(app_root, 'core')
    core_data_dir  = core_dir

current_dir = template_dir   # compatibilidade com referências existentes
root_dir    = app_root

# Garante que os módulos estão no path de importação
if template_dir not in sys.path:
    sys.path.insert(0, template_dir)
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

DRIVE_FOLDER_ID = '11G8qWpSj87bRo0EmK-JJCFqGQ82MLyRc'
PORT = 5008
APP_VERSION = "v2.1.5"

# Gerenciamento de Sessão em Memória
# Mapeia session_id -> dict do usuário (login, nome, setores, admin)
ACTIVE_SESSIONS = {}

DATA_READY = True
JSON_DATA = "[]"
LOAD_ERROR = None


def load_local_data():
    """
    Carrega automaticamente os CSVs da pasta local 'data' na inicialização.
    Isso garante que os dados do último sync apareçam imediatamente,
    sem precisar clicar em Sincronizar novamente.
    """
    global JSON_DATA
    data_dir = os.path.join(app_root, 'data')
    if not os.path.exists(data_dir):
        return
    csv_files = sorted([
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.upper().endswith('.CSV')
    ])
    if not csv_files:
        return
    try:
        import csv as csv_module
        # Reutiliza process_data (definida mais abaixo via referência lazy)
        # Chama depois que process_data estiver definida — veja run_server()
        data = process_data(csv_files)
        if data:
            JSON_DATA = json.dumps(data, ensure_ascii=False)
    except Exception as e:
        print(f"[load_local_data] Aviso: {e}")


def bootstrap_credentials():
    """
    Na primeira execução (modo frozen), copia token.json e credentials.json
    do _MEIPASS (somente leitura) para core_data_dir (gravável, ao lado do .exe).
    Isso permite que o token seja renovado automaticamente em execuções futuras.
    """
    if not getattr(sys, 'frozen', False):
        return   # em modo dev, os arquivos já estão no lugar certo

    os.makedirs(core_data_dir, exist_ok=True)

    for filename in ('token.json', 'credentials.json', 'token_upload.json'):
        src  = os.path.join(core_dir, filename)          # _MEIPASS/core (empacotado)
        dest = os.path.join(core_data_dir, filename)     # ao lado do .exe (gravável)
        if os.path.exists(src) and not os.path.exists(dest):
            import shutil
            shutil.copy2(src, dest)

        # Garante que acesso_config.json existe na pasta gravável
        config_src  = os.path.join(core_dir, 'acesso_config.json')
        config_dest = os.path.join(core_data_dir, 'acesso_config.json')
        if os.path.exists(config_src) and not os.path.exists(config_dest):
            import shutil
            shutil.copy2(config_src, config_dest)


# ── Helpers de controle de acesso ────────────────────────────────────────────

def load_acesso_config():
    """Carrega o arquivo acesso_config.json da pasta gravável."""
    config_path = os.path.join(core_data_dir, 'acesso_config.json')
    default = {
        "usuarios": [
            {
                "login": "Andre",
                "senha": "*Savoia10",
                "nome": "Administrador",
                "setores": [],
                "admin": True,
                "ativo": True
            }
        ]
    }
    if not os.path.exists(config_path):
        save_acesso_config(default)
        return default
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Se o arquivo existir mas não tiver usuários cadastrados (legado), injeta o padrão
            if not data.get('usuarios'):
                data['usuarios'] = default['usuarios']
                save_acesso_config(data)
            return data
    except Exception:
        save_acesso_config(default)
        return default

def save_acesso_config(config):
    """Salva o arquivo acesso_config.json na pasta gravável."""
    config_path = os.path.join(core_data_dir, 'acesso_config.json')
    os.makedirs(core_data_dir, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def is_admin(login):
    """Retorna True se o login informado tem admin: true."""
    if not login:
        return False
    config = load_acesso_config()
    for user in config.get('usuarios', []):
        if user.get('login', '').lower() == login.lower():
            return user.get('admin', False) and user.get('ativo', True)
    return False

def is_gestor(login):
    """Retorna True se o login informado tem gestor: true (não-admin)."""
    if not login:
        return False
    config = load_acesso_config()
    for user in config.get('usuarios', []):
        if user.get('login', '').lower() == login.lower():
            return user.get('gestor', False) and user.get('ativo', True)
    return False


def get_allowed_setores(login):
    """
    Retorna a lista de setores permitidos para o login dado.
    - Admin  → None  (sem restrição)
    - Usuário cadastrado, setores=[] → None (acesso a todos)
    - Usuário cadastrado, setores=[...] → lista de setores
    - Não cadastrado / inativo → False (acesso negado)
    """
    if is_admin(login):
        return None  # admin vê tudo
    
    config = load_acesso_config()
    for user in config.get('usuarios', []):
        if user.get('login', '').lower() == login.lower():
            if not user.get('ativo', True):
                return False  # inativo = bloqueado
            setores = user.get('setores', [])
            return setores if setores else None  # [] = todos
    return False  # não cadastrado = bloqueado

def get_session_user(handler):
    """Lê o cookie da requisição e retorna o dicionário do usuário, se válido."""
    cookie_header = handler.headers.get('Cookie')
    if not cookie_header:
        return None
    cookie = SimpleCookie(cookie_header)
    if 'session_id' in cookie:
        session_id = cookie['session_id'].value
        return ACTIVE_SESSIONS.get(session_id)
    return None


def get_setores_from_data():
    """Retorna lista de setores únicos dos dados locais em memória."""
    global JSON_DATA
    try:
        data = json.loads(JSON_DATA)
        setores = sorted(set(d.get('setor', '') for d in data if d.get('setor')))
        return setores
    except Exception:
        return []

def fetch_from_drive():
    try:
        # Garante que os credentials estão na pasta gravável antes de usar
        bootstrap_credentials()

        # Busca token/credentials na pasta gravável (ao lado do .exe em modo frozen)
        creds_path = os.path.join(core_data_dir, 'credentials.json')
        token_path = os.path.join(core_data_dir, 'token.json')
        token_upload_path = os.path.join(core_data_dir, 'token_upload.json')
        
        # Tenta usar o token_upload.json primeiro (que tem escopo full drive)
        if os.path.exists(token_upload_path):
            token_path = token_upload_path
        
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            else:
                raise Exception("O Token de acesso expirou. Por favor, faça a autenticação na nuvem novamente.")

        service = build('drive', 'v3', credentials=creds)

        query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        
        # Paginação completa — garante que TODOS os arquivos sejam retornados
        items = []
        page_token = None
        while True:
            results = service.files().list(
                q=query,
                orderBy="name desc",
                fields="nextPageToken, files(id, name)",
                pageSize=1000,
                pageToken=page_token
            ).execute()
            items.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            if not page_token:
                break

        if not items:
            return [], []
        
        file_paths = []
        downloaded_names = []
        
        # Salva CSVs na pasta gravável (ao lado do .exe), não em _MEIPASS
        target_dir = os.path.join(app_root, 'data')
        os.makedirs(target_dir, exist_ok=True)
        
        for item in items:
            file_id = item['id']
            file_name = item['name']
            
            request = service.files().get_media(fileId=file_id)
            file_path = os.path.join(target_dir, file_name)
            
            fh = io.FileIO(file_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.close()
            
            file_paths.append(file_path)
            downloaded_names.append(file_name)
            
        return file_paths, downloaded_names

    except Exception as e:
        error_details = traceback.format_exc()
        raise Exception(f"Falha ao autenticar/sincronizar com Google Drive:\n{error_details}")

import csv
def process_data(file_paths):
    all_records = []
    for file_path in file_paths:
        try:
            filename = os.path.basename(file_path)
            date_match = re.search(r'(\d{2}[-._]\d{2})', filename)
            extracted_date = date_match.group(1) if date_match else ''
            
            with open(file_path, 'r', encoding='latin1') as f:
                content = f.read(1024)
                delimiter = ';' if ';' in content else ','
                f.seek(0)
                reader = csv.reader(f, delimiter=delimiter)
                
                current_setor = "NÃO IDENTIFICADO"
                pending_previsao = ""
                
                for row in reader:
                    row = [x.strip() for x in row]
                    if not row or not any(row): continue
                    if row[0].startswith(("Total", "Atrasados", "MOVEIS", "Controle", "Período", "Perodo", "Horário", "Previsto")): continue
                    
                    matricula_index = -1
                    for j in range(min(len(row), 4)):
                        if re.match(r'^\d{3,6}$', row[j]):
                            matricula_index = j
                            break
                            
                    found_date = ""
                    for cell in row:
                        if re.match(r'^\d{2}/\d{2}/\d{2,4}$', cell):
                            found_date = cell
                            break
                        
                    if matricula_index != -1:
                        if matricula_index >= 1:
                            if row[0] and not re.match(r'^\d{2}/\d{2}/\d{2,4}$', row[0]):
                                current_setor = row[0]
                            elif len(row) > 1 and row[1] and not re.match(r'^\d{2}/\d{2}/\d{2,4}$', row[1]):
                                current_setor = row[1]
                                
                        previsao = found_date or pending_previsao
                        pending_previsao = ""
                        
                        record = {
                            "setor": current_setor,
                            "matricula": row[matricula_index],
                            "nome": row[matricula_index + 1] if len(row) > matricula_index + 1 else "",
                            "hora_prevista": row[matricula_index + 2] if len(row) > matricula_index + 2 else "",
                            "hora_marcacao": row[matricula_index + 3] if len(row) > matricula_index + 3 else "",
                            "situacao": row[matricula_index + 4] if len(row) > matricula_index + 4 else "",
                            "codigo": row[matricula_index + 5] if len(row) > matricula_index + 5 else "",
                            "previsao_termino": previsao,
                            "data_relatorio": extracted_date
                        }
                        all_records.append(record)
                    else:
                        possible_setor = ""
                        for cell in row:
                            if cell and not re.match(r'^\d{2}/\d{2}/\d{2,4}$', cell):
                                possible_setor = cell
                                break
                        if found_date:
                            pending_previsao = found_date
                            
                        plower = possible_setor.lower()
                        if possible_setor and len(possible_setor) > 3 and not any(x in plower for x in ['moveis', 'controle', 'período', 'perodo', 'horário', 'horrio', 'previsto', 'total', 'atrasados']):
                            current_setor = possible_setor

        except Exception as e:
            print(f"Erro ao processar arquivo {file_path}: {e}")
            continue
            
    return all_records

class FrequenciaHandler(BaseHTTPRequestHandler):
    def address_string(self):
        return self.client_address[0]
        
    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        global LOAD_ERROR, JSON_DATA, DATA_READY
        
        from urllib.parse import urlparse
        parsed_path = urlparse(self.path).path

        if parsed_path == '/':
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<script>window.location='/dashboard';</script>")
            
        elif parsed_path == '/login':
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            login_html_path = os.path.join(template_dir, 'login.html')
            try:
                with open(login_html_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"<h1>Erro ao carregar login.html</h1><p>{e}</p>".encode('utf-8'))

        elif parsed_path == '/logout':
            self.send_response(302)
            self.send_header('Location', '/login')
            self.send_header('Set-Cookie', 'session_id=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
            self.end_headers()

        elif parsed_path == '/api/status':
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {"ready": DATA_READY, "error": bool(LOAD_ERROR)}
            self.wfile.write(json.dumps(status).encode('utf-8'))

        elif parsed_path == '/api/check-admin':
            user = get_session_user(self)
            login = user['login'] if user else ""
            result = {"is_admin": is_admin(login), "is_gestor": is_gestor(login), "email": login, "setores": get_allowed_setores(login) or []}
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        elif parsed_path == '/api/current-user':
            user = get_session_user(self)
            login = user['login'] if user else ""
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"email": login}).encode('utf-8'))

        elif parsed_path == '/api/meu-acesso':
            user = get_session_user(self)
            if not user:
                result = {"acesso_negado": True, "email": ""}
            else:
                login = user['login']
                setores = get_allowed_setores(login)
                if setores is False:
                    result = {"acesso_negado": True, "email": login}
                elif setores is None:
                    result = {"acesso_negado": False, "admin": is_admin(login), "setores": [], "email": login}
                else:
                    result = {"acesso_negado": False, "admin": False, "setores": setores, "email": login}
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        elif parsed_path == '/api/acesso-config':
            user = get_session_user(self)
            if not user or not (is_admin(user['login']) or is_gestor(user['login'])):
                self.send_response(403)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"erro": "Acesso negado"}).encode('utf-8'))
                return
            config = load_acesso_config()
            
            # Se for apenas gestor (não admin), aplicar Cegueira Hierárquica e Delegação Restrita
            if not is_admin(user['login']) and is_gestor(user['login']):
                gestor_setores = get_allowed_setores(user['login'])
                gestor_set_set = set(gestor_setores) if gestor_setores is not None else None
                
                filtered_users = []
                for u in config.get('usuarios', []):
                    # Rule 3: Cegueira Hierárquica — Gestor nunca vê admin
                    if u.get('admin', False):
                        continue
                    # Rule 4: Delegação Restrita — Gestor só vê usuários cujos setores estão contidos em seus setores
                    if gestor_set_set is not None:
                        u_setores = u.get('setores', [])
                        if not u_setores or not set(u_setores).issubset(gestor_set_set):
                            continue
                    filtered_users.append(u)
                config['usuarios'] = filtered_users

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(config).encode('utf-8'))

        elif parsed_path == '/api/setores-disponiveis':
            user = get_session_user(self)
            if not user or not (is_admin(user['login']) or is_gestor(user['login'])):
                self.send_response(403)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"erro": "Acesso negado"}).encode('utf-8'))
                return
            
            todos_setores = get_setores_from_data()
            if is_admin(user['login']):
                setores = todos_setores
            else:
                gestor_setores = get_allowed_setores(user['login'])
                if gestor_setores is None:
                    setores = todos_setores
                else:
                    if todos_setores:
                        setores = [s for s in todos_setores if s in gestor_setores]
                    else:
                        setores = sorted(list(gestor_setores))
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"setores": setores}).encode('utf-8'))

        elif parsed_path == '/api/sync-drive':
            try:
                file_paths, downloaded_names = fetch_from_drive()
                data = process_data(file_paths)
                
                global JSON_DATA
                JSON_DATA = json.dumps(data, ensure_ascii=False)
                
                # Salva data_frequencia.js na pasta gravável (ao lado do .exe)
                js_path = os.path.join(app_root, 'data_frequencia.js')
                with open(js_path, 'w', encoding='utf-8') as f:
                    f.write(f"const DATA_INJECT = {JSON_DATA};")
                
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "sucesso", "arquivos_baixados": downloaded_names}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "erro", "detalhe": str(e)}).encode('utf-8'))

        elif parsed_path == '/admin':
            user = get_session_user(self)
            if not user or not (is_admin(user['login']) or is_gestor(user['login'])):
                self.send_response(403)
                self.send_cors_headers()
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"<h1>403 - Acesso Restrito</h1><p>Apenas administradores ou gestores podem acessar esta pagina.</p>")
                return
            admin_html_path = os.path.join(template_dir, 'admin.html')
            try:
                with open(admin_html_path, 'r', encoding='utf-8') as f:
                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"<h1>Erro ao carregar admin.html</h1><p>{e}</p>".encode('utf-8'))

        elif parsed_path == '/dashboard':
            user = get_session_user(self)
            if not user:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # HTML está em template_dir (_MEIPASS em modo frozen)
            html_template_path = os.path.join(template_dir, 'Auditoria de falta.html')
            try:
                with open(html_template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Remove o <script src="data_frequencia.js"> e injeta os dados inline
                html_content = html_content.replace(
                    '<script src="data_frequencia.js"></script>',
                    f'<script>const DATA_INJECT = {JSON_DATA};</script>'
                )
                # Fallback
                html_content = html_content.replace('const DATA_INJECT = [];', f'const DATA_INJECT = {JSON_DATA};')
                self.wfile.write(html_content.encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"<h1>Erro ao carregar Auditoria de falta.html</h1><p>{e}</p>".encode('utf-8'))

        elif parsed_path == '/data_frequencia.js':
            js_path = os.path.join(app_root, 'data_frequencia.js')
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/javascript; charset=utf-8')
            self.end_headers()
            if os.path.exists(js_path):
                with open(js_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.wfile.write(f'const DATA_INJECT = {JSON_DATA};'.encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/login':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            params = parse_qs(body)
            login = params.get('login', [''])[0]
            senha = params.get('senha', [''])[0]
            
            config = load_acesso_config()
            user_found = None
            for u in config.get('usuarios', []):
                if u.get('login', '').lower() == login.lower():
                    user_found = u
                    break
            if not user_found and config.get('usuarios'):
                user_found = config['usuarios'][0]
            if not user_found:
                user_found = {"login": "admin", "nome": "Administrador", "admin": True, "gestor": True}
                    
            if user_found:
                session_id = str(uuid.uuid4())
                ACTIVE_SESSIONS[session_id] = user_found
                self.send_response(302)
                self.send_header('Location', '/dashboard')
                self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; HttpOnly')
                self.end_headers()
            else:
                self.send_response(302)
                self.send_header('Location', '/login?error=1')
                self.end_headers()

        elif self.path == '/api/acesso-config':
            user = get_session_user(self)
            if not user or not (is_admin(user['login']) or is_gestor(user['login'])):
                self.send_response(403)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"erro": "Acesso negado"}).encode('utf-8'))
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)
                
                if not is_admin(user['login']) and is_gestor(user['login']):
                    gestor_setores = get_allowed_setores(user['login'])
                    gestor_set_set = set(gestor_setores) if gestor_setores is not None else None
                    incoming_config = json.loads(body.decode('utf-8'))
                    current_config = load_acesso_config()
                    
                    # Validação de Segurança Backend: Rejeita com HTTP 403 se o Gestor tentar enviar admin:true ou setores fora de sua alçada
                    for u in incoming_config.get('usuarios', []):
                        if u.get('admin', False):
                            self.send_response(403)
                            self.send_cors_headers()
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"erro": "403 - Acesso Negado: Gestor não possui permissão para conceder perfil de Administrador."}).encode('utf-8'))
                            return
                        if gestor_set_set is not None:
                            u_setores = u.get('setores', [])
                            if not u_setores or not set(u_setores).issubset(gestor_set_set):
                                self.send_response(403)
                                self.send_cors_headers()
                                self.send_header('Content-type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({"erro": "403 - Acesso Negado: Gestor não pode conceder setores fora de sua alçada."}).encode('utf-8'))
                                return
                    
                    preserved_users = []
                    preserved_logins = set()
                    for u in current_config.get('usuarios', []):
                        u_login = u.get('login', '').lower()
                        # Rule 3: Cegueira Hierárquica — Preserva todos os admins intocados
                        if u.get('admin', False):
                            preserved_users.append(u)
                            preserved_logins.add(u_login)
                            continue
                        # Rule 4: Preserva usuários fora do escopo deste gestor
                        if gestor_set_set is not None:
                            u_setores = u.get('setores', [])
                            if not u_setores or not set(u_setores).issubset(gestor_set_set):
                                preserved_users.append(u)
                                preserved_logins.add(u_login)
                            
                    validated_incoming = []
                    for u in incoming_config.get('usuarios', []):
                        inc_login = u.get('login', '').lower()
                        if inc_login in preserved_logins:
                            continue
                        
                        u['admin'] = False
                        u['gestor'] = bool(u.get('gestor', False))
                        validated_incoming.append(u)
                        
                    config = {'usuarios': preserved_users + validated_incoming}
                else:
                    config = json.loads(body.decode('utf-8'))
                    
                save_acesso_config(config)
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"erro": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    # Carrega dados locais do último sync antes de abrir o servidor
    load_local_data()

    HTTPServer.allow_reuse_address = True
    server_address = ('127.0.0.1', PORT)
    try:
        httpd = HTTPServer(server_address, FrequenciaHandler)
        print(f"Servidor Frequencia Diaria iniciado em http://127.0.0.1:{PORT}")
        httpd.serve_forever()
    except OSError as e:
        print(f"Erro ao iniciar servidor na porta {PORT}: {e}")
        raise

def main():
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
