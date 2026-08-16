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
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser
import uuid
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import hashlib

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
APP_VERSION = "v2.4.4"

# Gerenciamento de Sessão em Memória
# Mapeia session_id -> dict do usuário (login, nome, setores, admin)
ACTIVE_SESSIONS = {}

DATA_READY = True
JSON_DATA = "[]"
HEADCOUNT_DATA = {"by_mat": {}, "by_sector": {}, "total": 0}
HEADCOUNT_JSON = '{"by_mat": {}, "by_sector": {}, "total": 0}'
HEADCOUNT_HISTORY_DATA = {"history": {}, "competencias": [], "latest_competencia": ""}
HEADCOUNT_HISTORY_JSON = '{"history": {}, "competencias": [], "latest_competencia": ""}'
LOAD_ERROR = None


def clean_setor_name(s):
    if not s: return s
    s = s.strip()
    # Normalização de duplicidades históricas
    if s.upper() in ["TAPEÇARIA GERAL", "TAPEÇARIA COLAGEM"]:
        return "TAPEÇARIA"
    return s


def load_datalake():
    global JSON_DATA, HEADCOUNT_DATA, HEADCOUNT_JSON, HEADCOUNT_HISTORY_DATA, HEADCOUNT_HISTORY_JSON
    
    # Busca pasta datalake prioritariamente no app_root (persistente no HD real)
    datalake_dir = os.path.join(app_root, 'data', 'datalake')
    if not os.path.exists(datalake_dir) or not os.listdir(datalake_dir):
        # Fallback para o embutido no _MEIPASS (efeito Matrioska)
        datalake_dir = os.path.join(template_dir, 'data', 'datalake')
        
    freq_path = os.path.join(datalake_dir, 'datalake_frequencia.json')
    hc_path = os.path.join(datalake_dir, 'datalake_headcount.json')
    history_path = os.path.join(datalake_dir, 'datalake_headcount_history.json')

    if not (os.path.exists(freq_path) and os.path.exists(hc_path) and os.path.exists(history_path)):
        print("[load_datalake] Arquivos do Data Lake não encontrados. Executando ETL autônomo...")
        try:
            import etl_datalake
            etl_datalake.run_etl()
        except Exception as e:
            print(f"[load_datalake] Erro ao executar ETL: {e}")

    try:
        if os.path.exists(freq_path):
            with open(freq_path, 'r', encoding='utf-8') as f:
                freq_data = json.load(f)
                JSON_DATA = json.dumps(freq_data, ensure_ascii=False)

        if os.path.exists(hc_path):
            with open(hc_path, 'r', encoding='utf-8') as f:
                HEADCOUNT_DATA = json.load(f)
                HEADCOUNT_JSON = json.dumps(HEADCOUNT_DATA, ensure_ascii=False)

        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                HEADCOUNT_HISTORY_DATA = json.load(f)
                HEADCOUNT_HISTORY_JSON = json.dumps(HEADCOUNT_HISTORY_DATA, ensure_ascii=False)

        print(f"[load_datalake] SUCESSO: Data Lake em memória. Frequência: {len(json.loads(JSON_DATA))} registros | Headcount Total: {HEADCOUNT_DATA.get('total')}")
    except Exception as e:
        print(f"[load_datalake] ERRO ao carregar Data Lake: {e}")



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


# ── Cache Global para IAM Cloud-First ─────────────────────────────────────────
IAM_CACHE = {
    'config': None,
    'modified_time': None
}

def get_drive_service_for_iam():
    bootstrap_credentials()
    token_path = os.path.join(core_data_dir, 'token_upload.json')
    if not os.path.exists(token_path):
        token_path = os.path.join(core_data_dir, 'token.json')
        
    creds = Credentials.from_authorized_user_file(token_path)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

# ── Helpers de controle de acesso ────────────────────────────────────────────

def load_acesso_config():
    """Carrega o arquivo acesso_config_cloud.json do Google Drive com Cache."""
    global IAM_CACHE
    CLOUD_FILENAME = 'acesso_config_cloud.json'
    
    default = {
        "usuarios": [
            {
                "login": "Andre",
                "senha": "sha256$" + hashlib.sha256(b"*Savoia10").hexdigest(),
                "nome": "Administrador",
                "setores": [],
                "admin": True,
                "ativo": True
            }
        ]
    }
    
    try:
        service = get_drive_service_for_iam()
        query = f"name='{CLOUD_FILENAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, modifiedTime)").execute()
        items = results.get('files', [])
        
        if not items:
            save_acesso_config(default)
            return default
            
        file_id = items[0]['id']
        modified_time = items[0].get('modifiedTime')
        
        # Hit Cache se modifiedTime não mudou
        if IAM_CACHE['config'] and IAM_CACHE['modified_time'] == modified_time:
            return copy.deepcopy(IAM_CACHE['config'])
            
        # Baixa arquivo se mudou
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        data = json.loads(fh.read().decode('utf-8'))
        
        # Salva em Cache
        IAM_CACHE['config'] = data
        IAM_CACHE['modified_time'] = modified_time
        return copy.deepcopy(data)
        
    except Exception as e:
        print(f"Erro no load_acesso_config (IAM Cloud): {e}")
        return copy.deepcopy(IAM_CACHE['config']) if IAM_CACHE['config'] else copy.deepcopy(default)

def save_acesso_config(config):
    """Salva o arquivo acesso_config_cloud.json no Google Drive."""
    global IAM_CACHE
    CLOUD_FILENAME = 'acesso_config_cloud.json'
    try:
        service = get_drive_service_for_iam()
        
        # Garante que senhas novas tenham hash
        for u in config.get('usuarios', []):
            senha = u.get('senha', '')
            if senha and not senha.startswith('sha256$'):
                u['senha'] = 'sha256$' + hashlib.sha256(senha.encode('utf-8')).hexdigest()
                
        # Atualiza Cache Local
        IAM_CACHE['config'] = config
        import datetime
        IAM_CACHE['modified_time'] = datetime.datetime.utcnow().isoformat() + 'Z'
        
        # Salva em temp
        temp_path = os.path.join(app_root, 'temp_acesso_config.json')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
        media = MediaFileUpload(temp_path, mimetype='application/json')
        
        query = f"name='{CLOUD_FILENAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        if items:
            service.files().update(fileId=items[0]['id'], media_body=media).execute()
        else:
            file_metadata = {'name': CLOUD_FILENAME, 'parents': [DRIVE_FOLDER_ID]}
            service.files().create(body=file_metadata, media_body=media).execute()
            
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    except Exception as e:
        print(f"Erro ao salvar acesso_config no Drive: {e}")

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



class FrequenciaHandler(BaseHTTPRequestHandler):
    def address_string(self):
        return self.client_address[0]
        
    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')

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
                    result = {"acesso_negado": False, "admin": is_admin(login), "gestor": is_gestor(login), "setores": [], "email": login}
                else:
                    result = {"acesso_negado": False, "admin": is_admin(login), "gestor": is_gestor(login), "setores": setores, "email": login}
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
                    # Gestor não vê Administradores (ex: Andre) nem outros Gestores
                    if u.get('admin', False) or u.get('gestor', False):
                        continue
                    # Gestor só vê gerentes cujos setores pertencem ao seu escopo
                    if gestor_set_set is not None:
                        u_setores = u.get('setores', [])
                        if u_setores and not set(u_setores).issubset(gestor_set_set):
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
            self.wfile.write(json.dumps({"setores": setores}, ensure_ascii=False).encode('utf-8'))
        elif parsed_path == '/api/top-absenteismo':
            from urllib.parse import parse_qs, urlparse
            query_params = parse_qs(urlparse(self.path).query)
            visao = query_params.get('visao', ['semana'])[0]
            mes_sel = query_params.get('mes', [''])[0]
            sem_sel = query_params.get('semana', [''])[0]
            setor_sel = query_params.get('setor', [''])[0]
            limit = int(query_params.get('limit', [20])[0])

            user = get_session_user(self)
            login = user['login'] if user else ""
            allowed_setores = get_allowed_setores(login) if login else None

            try:
                records = json.loads(JSON_DATA)
            except Exception:
                records = []

            filtered = []
            for r in records:
                sit = r.get('situacao', '')
                if sit and any(kw in sit.upper() for kw in ['AUX', 'DOEN', 'ATESTAD', 'MATERN', 'FERIA', 'INVALIDEZ', 'AVISO', 'PREVIO', 'AFASTAD', 'LICENC']):
                    continue

                setor_rec = clean_setor_name(r.get('setor', ''))
                if allowed_setores is not False and allowed_setores is not None:
                    allowed_clean = [clean_setor_name(s) for s in allowed_setores]
                    if setor_rec not in allowed_clean:
                        continue

                if setor_sel and clean_setor_name(setor_sel) != setor_rec:
                    continue

                date_str = r.get('data_relatorio') or r.get('data_ponto') or ''

                if visao == 'semana':
                    if mes_sel:
                        parts = re.split(r'[/|-]', date_str)
                        if len(parts) >= 2 and parts[1] != mes_sel:
                            continue
                elif visao == 'mes':
                    if mes_sel:
                        parts = re.split(r'[/|-]', date_str)
                        if len(parts) >= 2 and parts[1] != mes_sel:
                            continue

                filtered.append(r)

            emp_map = {}
            for r in filtered:
                mat = r.get('matricula', '')
                nome = r.get('nome', 'NÃO IDENTIFICADO')
                setor = clean_setor_name(r.get('setor', ''))
                key = mat or nome

                if key not in emp_map:
                    emp_map[key] = {
                        "matricula": mat,
                        "nome": nome,
                        "setor": setor,
                        "total_faltas": 0
                    }
                emp_map[key]["total_faltas"] += 1

            top_list = sorted(emp_map.values(), key=lambda x: x["total_faltas"], reverse=True)[:limit]

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"visao": visao, "total": len(top_list), "ranking": top_list}, ensure_ascii=False).encode('utf-8'))

        elif parsed_path == '/api/sync-drive':
            try:
                import etl_datalake
                meta = etl_datalake.run_etl()
                load_datalake()
                
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "sucesso", "metadata": meta}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "erro", "mensagem": str(e), "detalhe": str(e)}, ensure_ascii=False).encode('utf-8'))

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
                
                # Dynamic Version Injection
                current_version = "v2.4.2"
                version_path = os.path.join(core_dir, 'version_FrequenciaDiaria.json')
                if not os.path.exists(version_path):
                    version_path = os.path.join(core_dir, 'version.json')
                    
                if os.path.exists(version_path):
                    try:
                        with open(version_path, 'r', encoding='utf-8') as vf:
                            vdata = json.load(vf)
                            current_version = "v" + vdata.get('version', '2.4.2')
                    except Exception:
                        pass
                
                # Regex to replace the hardcoded version in the badge
                html_content = re.sub(r'(<span[^>]*badge-navy[^>]*>)[^<]*(</span>)', r'\g<1>' + current_version + r'\2', html_content)
                
                self.wfile.write(html_content.encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"<h1>Erro ao carregar Auditoria de falta.html</h1><p>{e}</p>".encode('utf-8'))

        elif parsed_path == '/data_frequencia.js':
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/javascript; charset=utf-8')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.end_headers()
            js_payload = f'const DATA_INJECT = {JSON_DATA};\nconst HEADCOUNT_INJECT = {HEADCOUNT_JSON};\nconst HEADCOUNT_HISTORY_INJECT = {HEADCOUNT_HISTORY_JSON};\nif(typeof window.onDataLoaded === "function") {{ window.onDataLoaded(); }}'
            self.wfile.write(js_payload.encode('utf-8'))

        elif parsed_path.endswith('.js'):
            filename = os.path.basename(parsed_path)
            js_path = os.path.join(template_dir, filename)
            if not os.path.exists(js_path):
                js_path = os.path.join(app_root, filename)
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-type', 'application/javascript; charset=utf-8')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.end_headers()
            if os.path.exists(js_path):
                with open(js_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b'// JS file not found')

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/login':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            params = parse_qs(body)
            login = params.get('login', [''])[0].strip()
            senha = params.get('senha', [''])[0].strip()
            config = load_acesso_config()
            user_found = None
            if login and senha:
                senha_hash = 'sha256$' + hashlib.sha256(senha.encode('utf-8')).hexdigest()
                for u in config.get('usuarios', []):
                    u_login = u.get('login', '').strip()
                    u_senha = u.get('senha', '').strip()
                    u_ativo = u.get('ativo', True)
                    # Compara com o hash, ou com a senha plana para retrocompatibilidade momentânea se necessário
                    if u_login.lower() == login.lower() and (u_senha == senha_hash or u_senha == senha) and u_ativo:
                        user_found = u
                        break
                    
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
                
                # DIAGNÓSTICO: Enviar os dados de sessão no erro para identificar a causa raiz
                user_login = user['login'] if user else 'None'
                is_adm = is_admin(user_login) if user else False
                is_ges = is_gestor(user_login) if user else False
                debug_msg = f"Acesso negado. Sessão={user_login}, Admin={is_adm}, Gestor={is_ges}"
                
                self.wfile.write(json.dumps({"erro": debug_msg}).encode('utf-8'))
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)
                
                if not is_admin(user['login']) and is_gestor(user['login']):
                    gestor_setores = get_allowed_setores(user['login'])
                    gestor_set_set = set(gestor_setores) if gestor_setores is not None else None
                    incoming_config = json.loads(body.decode('utf-8'))
                    current_config = load_acesso_config()
                    
                    # Validação de Segurança Backend: Gestor só possui permissão para cadastrar e gerenciar Gerentes
                    for u in incoming_config.get('usuarios', []):
                        if u.get('admin', False) or u.get('gestor', False):
                            self.send_response(403)
                            self.send_cors_headers()
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"erro": "403 - Acesso Negado: Gestor só possui permissão para gerenciar usuários Gerentes."}).encode('utf-8'))
                            return
                        if gestor_set_set is not None:
                            u_setores = u.get('setores', [])
                            if u_setores and not set(u_setores).issubset(gestor_set_set):
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
                        # Preserva todos os Admins (ex: Andre) e Gestores intocados
                        if u.get('admin', False) or u.get('gestor', False):
                            preserved_users.append(u)
                            preserved_logins.add(u_login)
                            continue
                        # Preserva usuários fora do escopo deste gestor
                        if gestor_set_set is not None:
                            u_setores = u.get('setores', [])
                            if u_setores and not set(u_setores).issubset(gestor_set_set):
                                preserved_users.append(u)
                                preserved_logins.add(u_login)
                            
                    validated_incoming = []
                    for u in incoming_config.get('usuarios', []):
                        inc_login = u.get('login', '').lower()
                        if inc_login in preserved_logins:
                            continue
                        
                        u['admin'] = False
                        u['gestor'] = False
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
    # Carrega o Data Lake em memória na inicialização do servidor
    try:
        load_datalake()
    except Exception as e:
        print(f"[run_server] AVISO: Erro durante load_datalake: {e}")
        import traceback
        traceback.print_exc()

    HTTPServer.allow_reuse_address = True
    server_address = ('0.0.0.0', PORT)
    try:
        httpd = HTTPServer(server_address, FrequenciaHandler)
        print(f"Servidor Absenteismo_plug iniciado em http://0.0.0.0:{PORT} (Local Network)")
        import socket
        hostname = socket.gethostname()
        print(f"Acesse na rede local via: http://{hostname}:{PORT}")
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
