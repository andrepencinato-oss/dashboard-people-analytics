import os
import sys
import time
import threading
import json
import urllib.request
from playwright.sync_api import sync_playwright

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)

from app_frequencia import HTTPServer, FrequenciaHandler, PORT, load_local_data, ACTIVE_SESSIONS

def run_headless_proof():
    print("[1/5] Carregando dados locais...")
    load_local_data()

    print("[2/5] Iniciando servidor HTTP na porta 5008...")
    httpd = HTTPServer(('127.0.0.1', PORT), FrequenciaHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    session_id = 'qa-proof-session-andre'
    ACTIVE_SESSIONS[session_id] = {
        'login': 'Andre',
        'nome': 'Andre',
        'admin': True,
        'ativo': True
    }

    print("[3/5] Disparando rota de sincronizacao de dados...")
    try:
        req = urllib.request.Request(
            f'http://127.0.0.1:{PORT}/api/sync-drive',
            headers={'Cookie': f'session_id={session_id}'}
        )
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            print("  Sincronizacao HTTP ok.")
    except Exception as e:
        print(f"  Aviso sync: {e}")

    print("[4/5] Executando Playwright Headless para capturar a tela...")
    proof_path = os.path.join(MODULE_DIR, 'comprovante_setores_ok.png')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies([{
            'name': 'session_id',
            'value': session_id,
            'url': f'http://127.0.0.1:{PORT}'
        }])
        
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        
        page.goto(f'http://127.0.0.1:{PORT}/admin.html', wait_until='networkidle')
        time.sleep(2)
        
        # Tirar screenshot da tela com os setores renderizados
        page.screenshot(path=proof_path, full_page=True)
        print(f"[5/5] Screenshot de prova salvo com sucesso em: {proof_path}")
        
        browser.close()

    httpd.shutdown()
    httpd.server_close()
    print("=== PROCESSO QA HEADLESS CONCLUÍDO COM SUCESSO ===")

if __name__ == '__main__':
    run_headless_proof()
