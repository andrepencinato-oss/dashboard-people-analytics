import urllib.request
import json
import time
import sys
import os

print("=== TESTANDO AVALIAÇÃO DE ESCOPOS DISTINTOS DO TRIPLO QUADRO ===")

import threading
from app_frequencia import HTTPServer, FrequenciaHandler, PORT, load_local_data, ACTIVE_SESSIONS

load_local_data()

test_session_id = "test-session-456"
ACTIVE_SESSIONS[test_session_id] = {
    "login": "Andre",
    "nome": "Administrador",
    "admin": True,
    "setores": [],
    "ativo": True
}

httpd = HTTPServer(('127.0.0.1', PORT), FrequenciaHandler)
server_thread = threading.Thread(target=httpd.serve_forever)
server_thread.daemon = True
server_thread.start()

time.sleep(1)

req = urllib.request.Request(f"http://127.0.0.1:{PORT}/dashboard")
req.add_header('Cookie', f'session_id={test_session_id}')

res_dash = urllib.request.urlopen(req)
status_dash = res_dash.getcode()
content_dash = res_dash.read().decode('utf-8')
print(f"GET /dashboard -> HTTP {status_dash} (Tamanho: {len(content_dash)} bytes)")

assert status_dash == 200, "Falha na rota /dashboard"
assert "targetMes = mesSel" in content_dash, "Lógica de escopo inteligente não encontrada no HTML"

httpd.shutdown()
print("[OK] TESTE CONCLUIDO COM SUCESSO!")
