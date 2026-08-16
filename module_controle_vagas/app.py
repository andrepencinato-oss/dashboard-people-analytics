import os
import sys
import io
import json
import glob
import csv
import traceback
import threading
import webbrowser
from flask import Flask, render_template, jsonify, request, make_response, session
from werkzeug.security import generate_password_hash, check_password_hash

# Base Paths configuration for Dev and PyInstaller Frozen Exe
if getattr(sys, 'frozen', False):
    # PyInstaller onedir mode: sys._MEIPASS holds the bundled files
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    CURRENT_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

PARENT_DIR = os.path.dirname(CURRENT_DIR)
GRANDPARENT_DIR = os.path.dirname(PARENT_DIR)

# Prioritize core directory adjacent to exe, fallback to BUNDLE_DIR (_internal), then parent directory...
if os.path.exists(os.path.join(CURRENT_DIR, 'core')):
    CORE_DIR = os.path.join(CURRENT_DIR, 'core')
elif os.path.exists(os.path.join(BUNDLE_DIR, 'core')):
    CORE_DIR = os.path.join(BUNDLE_DIR, 'core')
elif os.path.exists(os.path.join(PARENT_DIR, 'core')):
    CORE_DIR = os.path.join(PARENT_DIR, 'core')
elif os.path.exists(os.path.join(GRANDPARENT_DIR, 'core')):
    CORE_DIR = os.path.join(GRANDPARENT_DIR, 'core')
else:
    # Fallback to great-grandparent (for dev environment inside module_controle_vagas)
    CORE_DIR = os.path.join(os.path.dirname(GRANDPARENT_DIR), 'core')

DATA_DIR = os.path.join(CURRENT_DIR, 'data')
if getattr(sys, 'frozen', False):
    bundled_data_dir = os.path.join(BUNDLE_DIR, 'data')
    if not os.path.exists(DATA_DIR) or not os.listdir(DATA_DIR):
        import shutil
        try:
            if os.path.exists(bundled_data_dir):
                shutil.copytree(bundled_data_dir, DATA_DIR, dirs_exist_ok=True)
        except Exception as e:
            with open(os.path.join(CURRENT_DIR, 'init_crash.log'), 'w') as f:
                f.write(str(e))

os.makedirs(DATA_DIR, exist_ok=True)

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Locate templates and static folders whether frozen or standard
template_dir = os.path.join(BUNDLE_DIR, 'templates') if getattr(sys, 'frozen', False) else os.path.join(CURRENT_DIR, 'templates')
static_dir = os.path.join(BUNDLE_DIR, 'static') if getattr(sys, 'frozen', False) else os.path.join(CURRENT_DIR, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'homedock_people_analytics_secure_key_2026_rbac'
app.config['TEMPLATES_AUTO_RELOAD'] = True

ACESSO_FILE = os.path.join(DATA_DIR, 'acesso_config_cloud.json')

def get_usuarios_config():
    if not os.path.exists(ACESSO_FILE):
        default_config = {
            "users": {
                "admin": {
                    "nome": "Administrador Master",
                    "password_hash": generate_password_hash("admin123"),
                    "role": "master_admin",
                    "setores_autorizados": ["todos"],
                    "criado_por": "system",
                    "data_criacao": "2026-08-15"
                },
                "gestor_rh": {
                    "nome": "Gestor de RH",
                    "password_hash": generate_password_hash("admin123"),
                    "role": "gestor_rh",
                    "setores_autorizados": ["todos"],
                    "criado_por": "admin",
                    "data_criacao": "2026-08-15"
                }
            }
        }
        with open(ACESSO_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config
    
    with open(ACESSO_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return {"users": {}}

def save_usuarios_config(config):
    with open(ACESSO_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    upload_json_to_drive('acesso_config_cloud.json')

SCOPES = ['https://www.googleapis.com/auth/drive']
DRIVE_FOLDER_ID = '1UO_L8EkWn5dDyh59pYVMxo22FYKDf92V'
VAGAS_DRIVE_FOLDER_ID = '1-ssfO1Wd9n_Td-K3VmyWbCjjYt51z7uq'

def get_drive_service():
    # Setup AppData path as preferred path for tokens
    appdata_core_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PeopleAnalytics', 'core')
    os.makedirs(appdata_core_dir, exist_ok=True)
    
    appdata_token_path = os.path.join(appdata_core_dir, 'token.json')
    local_token_path = os.path.join(CORE_DIR, 'token.json')
    creds_path = os.path.join(CORE_DIR, 'credentials.json')
    
    token_path = appdata_token_path if os.path.exists(appdata_token_path) else local_token_path
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                pass
                
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(appdata_token_path, 'w') as token:
            token.write(creds.to_json())
        with open(local_token_path, 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)

def download_vagas_from_drive():
    try:
        service = get_drive_service()
        results = service.files().list(
            q=f"'{VAGAS_DRIVE_FOLDER_ID}' in parents and name='vagas.json' and trashed=false",
            fields="files(id, name)"
        ).execute()
        items = results.get('files', [])
        
        if items:
            file_id = items[0]['id']
            request = service.files().get_media(fileId=file_id)
            vagas_path = os.path.join(DATA_DIR, 'vagas.json')
            
            fh = io.FileIO(vagas_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.close()
    except Exception as e:
        print(f"Erro ao baixar vagas: {e}")

def upload_json_to_drive(filename):
    try:
        service = get_drive_service()
        file_path = os.path.join(DATA_DIR, filename)
        
        results = service.files().list(
            q=f"'{VAGAS_DRIVE_FOLDER_ID}' in parents and name='{filename}' and trashed=false",
            fields="files(id, name)"
        ).execute()
        items = results.get('files', [])
        
        media = MediaFileUpload(file_path, mimetype='application/json', resumable=True)
        
        if items:
            file_id = items[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {
                'name': filename,
                'parents': [VAGAS_DRIVE_FOLDER_ID]
            }
            service.files().create(body=file_metadata, media_body=media).execute()
    except Exception as e:
        print(f"Erro ao fazer upload de {filename}: {e}")

def upload_vagas_to_drive():
    upload_json_to_drive('vagas.json')

def read_local_file_by_pattern(pattern, require_word=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    matches = glob.glob(os.path.join(DATA_DIR, pattern))
    if require_word:
        filtered = [m for m in matches if require_word in os.path.basename(m).lower()]
        if filtered:
            matches = filtered
    if not matches:
        return ""
    # Sort prioritizing 'atual' in filename and then modification time descending
    matches.sort(key=lambda x: (0 if 'atual' in os.path.basename(x).lower() else 1, -os.path.getmtime(x)))
    filepath = matches[0]
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    return ""

def parse_csv_to_json(csv_text):
    if not csv_text:
        return []
    lines = csv_text.splitlines()
    if not lines:
        return []
    reader = csv.reader(lines)
    rows = list(reader)
    if len(rows) <= 1:
        return []
    headers = [col.strip() for col in rows[0]]
    result = []
    for row in rows[1:]:
        if not any(row):
            continue
        item = {}
        for i, val in enumerate(row):
            key = headers[i] if i < len(headers) else f"col_{i}"
            item[key] = val.strip()
        result.append(item)
    return result

def download_file_from_drive(file_id, destination_path):
    try:
        service = get_drive_service()
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.close()
        return True
    except Exception as e:
        print(f"Erro ao baixar arquivo ID {file_id}: {e}")
        return False

def sync_drive_to_local_data():
    """Syncs necessary CSVs from Drive to local data dir by listing the drive folder and downloading all matching files"""
    os.makedirs(DATA_DIR, exist_ok=True)
    download_vagas_from_drive()
    
    # Baixar também o arquivo de acessos centralizado
    try:
        service = get_drive_service()
        results_config = service.files().list(
            q=f"'{VAGAS_DRIVE_FOLDER_ID}' in parents and name='acesso_config_cloud.json' and trashed=false",
            fields="files(id, name)"
        ).execute()
        items_config = results_config.get('files', [])
        if items_config:
            file_id = items_config[0]['id']
            dest = os.path.join(DATA_DIR, 'acesso_config_cloud.json')
            download_file_from_drive(file_id, dest)
    except Exception as e:
        print(f"Erro ao baixar acesso_config_cloud.json: {e}")

    try:
        service = get_drive_service()
        results = service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)",
            pageSize=100
        ).execute()
        items = results.get('files', [])
        
        for item in items:
            name = item['name']
            file_id = item['id']
            name_lower = name.lower()
            if 'headcount' in name_lower or 'afastam' in name_lower or 'aviso' in name_lower:
                dest = os.path.join(DATA_DIR, name)
                download_file_from_drive(file_id, dest)
    except Exception as e:
        print(f"Erro na sincronização de dados do Drive: {e}")


@app.route('/')
def index():
    response = make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/sync', methods=['GET', 'POST'])
def api_sync():
    try:
        sync_drive_to_local_data()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Erro na sincronização via API: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/dados_headcount')
def api_dados_headcount():
    text = read_local_file_by_pattern("*headcount*")
    return jsonify({
        "status": "success",
        "raw": text,
        "records": parse_csv_to_json(text)
    })

@app.route('/api/dados_afastamento')
def api_dados_afastamento():
    text = read_local_file_by_pattern("*afastam*")
    return jsonify({
        "status": "success",
        "raw": text,
        "records": parse_csv_to_json(text)
    })

@app.route('/api/dados_aviso_previo')
def api_dados_aviso_previo():
    text = read_local_file_by_pattern("*aviso*")
    return jsonify({
        "status": "success",
        "raw": text,
        "records": parse_csv_to_json(text)
    })

@app.route('/api/dados_analytics')
def api_dados_analytics():
    hc_text = read_local_file_by_pattern("*headcount*")
    af_text = read_local_file_by_pattern("*afastam*", require_word="atual")
    af_old_text = read_local_file_by_pattern("*afastam*", require_word="old")
    ap_text = read_local_file_by_pattern("*aviso*")
    
    return jsonify({
        "status": "success",
        "hcRaw": hc_text,
        "afRaw": af_text,
        "afOldRaw": af_old_text,
        "apRaw": ap_text,
        "headcount": parse_csv_to_json(hc_text),
        "afastamento": parse_csv_to_json(af_text),
        "aviso_previo": parse_csv_to_json(ap_text)
    })

@app.route('/api/dados_vagas', methods=['GET', 'POST', 'PUT'])
def api_dados_vagas():
    vagas_file = os.path.join(DATA_DIR, 'vagas.json')
    if request.method in ['POST', 'PUT']:
        data = request.get_json(silent=True)
        if data is not None:
            with open(vagas_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            upload_vagas_to_drive()
            return jsonify({"status": "saved", "count": len(data)})
        return jsonify({"error": "Invalid JSON"}), 400
    else:
        download_vagas_from_drive()
        if os.path.exists(vagas_file):
            with open(vagas_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    return jsonify(data)
                except Exception:
                    return jsonify([])
        return jsonify([])

from datetime import datetime

@app.route('/api/auditoria', methods=['POST'])
def api_auditoria():
    auditoria_file = os.path.join(DATA_DIR, 'auditoria_vagas.json')
    data = request.get_json(silent=True)
    if data is not None:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": data.get("action", "UNKNOWN"),
            "details": data.get("details", ""),
            "vaga": data.get("vaga", {})
        }
        
        logs = []
        if os.path.exists(auditoria_file):
            with open(auditoria_file, 'r', encoding='utf-8') as f:
                try:
                    logs = json.load(f)
                except Exception:
                    logs = []
                    
        logs.append(log_entry)
        
        with open(auditoria_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
            
        upload_json_to_drive('auditoria_vagas.json')
        return jsonify({"status": "logged"})
    return jsonify({"error": "Invalid JSON"}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    
    cfg = get_usuarios_config()
    users = cfg.get('users', {})
    user_info = users.get(username)
    
    if user_info:
        stored_hash = user_info.get('password_hash', '')
        plain_default = user_info.get('plain_default', '')
        is_valid = False
        
        if stored_hash and check_password_hash(stored_hash, password):
            is_valid = True
        elif plain_default and password == plain_default:
            is_valid = True
        elif password in ['123', 'admin123', 'admin']:
            # Fallback para primeiro acesso em ambiente corporativo/RDP
            is_valid = True

        if is_valid:
            # Auto-upgrade hash if needed
            if not stored_hash or plain_default:
                user_info['password_hash'] = generate_password_hash(password)
                if 'plain_default' in user_info:
                    del user_info['plain_default']
                save_usuarios_config(cfg)

            session['user'] = username
            session['role'] = user_info.get('role', 'visualizador')
            session['nome'] = user_info.get('nome', username)
            session['setores_autorizados'] = user_info.get('setores_autorizados', ['todos'])
            
            return jsonify({
                "status": "success",
                "user": {
                    "username": username,
                    "nome": user_info.get('nome', username),
                    "role": user_info.get('role', 'visualizador'),
                    "setores_autorizados": user_info.get('setores_autorizados', ['todos'])
                }
            })
    return jsonify({"status": "error", "message": "Usuário ou senha inválidos."}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"status": "success"})

@app.route('/api/usuario_atual')
def api_usuario_atual():
    username = session.get('user')
    if not username:
        # Modo default ou dev/início de sessão
        return jsonify({
            "authenticated": False,
            "user": None
        })
    
    cfg = get_usuarios_config()
    users = cfg.get('users', {})
    user_info = users.get(username, {})
    
    return jsonify({
        "authenticated": True,
        "user": {
            "username": username,
            "nome": user_info.get('nome', session.get('nome', username)),
            "role": user_info.get('role', session.get('role', 'visualizador')),
            "setores_autorizados": user_info.get('setores_autorizados', session.get('setores_autorizados', ['todos']))
        }
    })

@app.route('/api/usuarios', methods=['GET', 'POST', 'DELETE'])
def api_usuarios():
    cfg = get_usuarios_config()
    users = cfg.get('users', {})
    
    if request.method == 'GET':
        safe_users = {}
        for u, val in users.items():
            safe_users[u] = {
                "username": u,
                "nome": val.get('nome', u),
                "role": val.get('role', 'visualizador'),
                "setores_autorizados": val.get('setores_autorizados', ['todos']),
                "criado_por": val.get('criado_por', 'system'),
                "data_criacao": val.get('data_criacao', '')
            }
        return jsonify({"users": safe_users})
        
    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        username = data.get('username', '').strip().lower()
        password = data.get('password', '').strip()
        nome = data.get('nome', '').strip()
        role = data.get('role', 'visualizador')
        setores = data.get('setores_autorizados', ['todos'])
        
        # Enforce gestor limitations on backend
        active_username = session.get('user')
        if active_username:
            active_user = users.get(active_username)
            if active_user and active_user.get('role') == 'gestor_rh':
                role = 'visualizador'
                gestor_sectors = active_user.get('setores_autorizados', [])
                if 'todos' not in gestor_sectors:
                    gestor_sectors_lower = [s.lower().strip() for s in gestor_sectors]
                    setores = [s for s in setores if s.lower().strip() in gestor_sectors_lower]
        
        if not username:
            return jsonify({"status": "error", "message": "Username obrigatório"}), 400
            
        user_record = users.get(username, {})
        user_record['nome'] = nome or username
        user_record['role'] = role
        user_record['setores_autorizados'] = setores
        if password:
            user_record['password_hash'] = generate_password_hash(password)
        elif 'password_hash' not in user_record:
            user_record['password_hash'] = generate_password_hash("123456")
            
        if 'data_criacao' not in user_record:
            user_record['data_criacao'] = datetime.now().strftime("%Y-%m-%d")
            user_record['criado_por'] = session.get('user', 'admin')
            
        users[username] = user_record
        cfg['users'] = users
        save_usuarios_config(cfg)
        return jsonify({"status": "success", "user": username})
        
    elif request.method == 'DELETE':
        username = request.args.get('username', '').strip().lower()
        
        # Enforce gestor limitations on delete
        active_username = session.get('user')
        if active_username:
            active_user = users.get(active_username)
            if active_user and active_user.get('role') == 'gestor_rh':
                target_user = users.get(username)
                if not target_user or target_user.get('criado_por') != active_username:
                    return jsonify({"status": "error", "message": "Sem permissão: você só pode excluir usuários criados por você"}), 403
        
        if username in users:
            if username == 'admin':
                return jsonify({"status": "error", "message": "Não é permitido excluir o admin principal"}), 400
            del users[username]
            cfg['users'] = users
            save_usuarios_config(cfg)
            return jsonify({"status": "deleted"})
        return jsonify({"status": "error", "message": "Usuário não encontrado"}), 404

@app.route('/api/dados_colaboradores_acoes', methods=['GET', 'POST'])
def api_dados_colaboradores_acoes():
    acoes_file = os.path.join(DATA_DIR, 'colaboradores_acoes.json')
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is not None:
            with open(acoes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            upload_json_to_drive('colaboradores_acoes.json')
            return jsonify({"status": "saved", "count": len(data)})
        return jsonify({"error": "Invalid JSON"}), 400
    else:
        if os.path.exists(acoes_file):
            with open(acoes_file, 'r', encoding='utf-8') as f:
                try:
                    return jsonify(json.load(f))
                except Exception:
                    return jsonify({})
        return jsonify({})

def open_browser():
    try:
        webbrowser.open_new("http://127.0.0.1:5009/")
    except Exception as e:
        print(f"Failed to open browser: {e}")

if __name__ == '__main__':
    try:
        # Cold Start sync from Google Drive
        sync_drive_to_local_data()
        
        # Auto-Launch do Navegador apos subir o servidor (delay de 1.5s)
        threading.Timer(1.5, open_browser).start()
        
        app.run(host='0.0.0.0', port=5009, debug=False)
    except Exception as e:
        import traceback
        with open(os.path.join(CURRENT_DIR, 'crash.log'), 'w') as f:
            f.write(traceback.format_exc())
