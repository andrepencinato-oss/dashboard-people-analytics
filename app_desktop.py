import excel_reader
import json
import re
import os
import sys
import webbrowser
import threading
import time
import traceback
import drive_sync
import pandas as pd
import io
from http.server import BaseHTTPRequestHandler, HTTPServer

if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

DATA_FILE_NAME = 'DP_-_Colaboradores_-_Extrato_Diário.xls'
APP_VERSION = "v2.0.2"

DATA_READY = False
JSON_DATA = "[]"
LOAD_ERROR = None
LAST_PING_TIME = time.time()

def background_load_data():
    global DATA_READY, JSON_DATA, LOAD_ERROR
    try:
        working_dir = get_working_dir()
        sync_file_path = drive_sync.fetch_latest_excel()
        extrato_path = sync_file_path if sync_file_path else os.path.join(working_dir, DATA_FILE_NAME)
        data = excel_reader.process_excel_files(extrato_path)
        JSON_DATA = json.dumps(data, ensure_ascii=False)
        DATA_READY = True
    except Exception as e:
        print(f"Erro no background load: {e}")
        LOAD_ERROR = str(e)
        try:
            with open(os.path.join(get_working_dir(), 'leitura_error_log.txt'), 'w', encoding='utf-8') as log_f:
                log_f.write(traceback.format_exc())
        except Exception:
            pass
        DATA_READY = True

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))

def get_working_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Disable logging to avoid console clutter
        pass

    def do_shutdown(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Shutting down')
        print("Shutdown requested. Exiting in 1 second...")
        # Delay shutdown to allow the browser to receive the response
        threading.Timer(1.0, lambda: os._exit(0)).start()

    def do_POST(self):
        if self.path == '/shutdown':
            self.do_shutdown()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        global LOAD_ERROR, JSON_DATA, DATA_READY, LAST_PING_TIME
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            base_path = get_base_path()
            loading_path = os.path.join(base_path, 'loading.html')
            
            try:
                with open(loading_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"<h1>Carregando dados...</h1><script>setInterval(() => fetch('/api/status').then(r=>r.json()).then(d=>{{if(d.ready) window.location='/dashboard';}}), 1000);</script>".encode('utf-8'))

        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {"ready": DATA_READY, "error": bool(LOAD_ERROR)}
            self.wfile.write(json.dumps(status).encode('utf-8'))

        elif self.path == '/dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            base_path = get_base_path()
            
            if LOAD_ERROR:
                emergency_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Erro de Sincronização</title>
                    <style>
                        body {{ background-color: #121212; color: #00ff00; font-family: monospace; padding: 2rem; }}
                        h1 {{ color: #ff3333; }}
                        .traceback {{ background: #222; padding: 1rem; border: 1px solid #555; white-space: pre-wrap; }}
                        .instruction {{ font-weight: bold; color: #fff; margin-bottom: 1rem; }}
                    </style>
                </head>
                <body>
                    <h1>Erro de Sincronização de Dados</h1>
                    <div class="instruction">Copiar o texto abaixo e enviar ao suporte técnico:</div>
                    <div class="traceback">{LOAD_ERROR}</div>
                </body>
                </html>
                """
                self.wfile.write(emergency_html.encode('utf-8'))
                return

            html_template_path = os.path.join(base_path, 'dashboard_dp_colaboradores.html')
            
            try:
                with open(html_template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                new_html_content = re.sub(
                    r'const COLAB = \[.*?\];', 
                    f'const COLAB = {JSON_DATA};', 
                    html_content, 
                    flags=re.DOTALL
                )

                new_html_content = new_html_content.replace('{{APP_VERSION}}', APP_VERSION)

                shutdown_script = """
<script>
    window.addEventListener('beforeunload', function (e) {
        navigator.sendBeacon('/shutdown');
    });
    setInterval(function() {
        fetch('/ping').catch(e => console.log('Heartbeat failed'));
    }, 5000);
</script>
</body>
"""
                if '</body>' in new_html_content:
                    new_html_content = new_html_content.replace('</body>', shutdown_script)
                else:
                    new_html_content += shutdown_script
                
                self.wfile.write(new_html_content.encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"<h1>Erro ao carregar dashboard</h1><p>{e}</p>".encode('utf-8'))
                
        elif self.path == '/shutdown':
            self.do_shutdown()
        elif self.path == '/api/exportar_excel':
            try:
                data_list = json.loads(JSON_DATA)
                df = pd.DataFrame(data_list)
                
                output = io.BytesIO()
                df.to_excel(output, index=False)
                excel_data = output.getvalue()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', 'attachment; filename="Auditoria de dados - Diario de bordo - Gestao de pessoas.xlsx"')
                self.end_headers()
                self.wfile.write(excel_data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Erro ao gerar Excel: {str(e)}".encode('utf-8'))
        elif self.path == '/ping':
            LAST_PING_TIME = time.time()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'pong')
        else:
            self.send_response(404)
            self.end_headers()

def main():
    # Verifica atualizações antes de iniciar qualquer thread
    import auto_updater
    auto_updater.check_and_apply_updates(APP_VERSION)

    # Inicia a thread de carregamento em background
    load_thread = threading.Thread(target=background_load_data)
    load_thread.daemon = True
    load_thread.start()

    HTTPServer.allow_reuse_address = True
    port = 5000
    httpd = None
    
    # Try finding an open port dynamically
    while port < 5050:
        try:
            server_address = ('127.0.0.1', port)
            httpd = HTTPServer(server_address, DashboardHandler)
            break
        except OSError:
            port += 1
            
    if not httpd:
        print("Não foi possível iniciar o servidor local. Nenhuma porta livre encontrada.")
        sys.exit(1)
        
    url = f"http://127.0.0.1:{port}"
    print(f"Servidor iniciado em {url}")
    
    global LAST_PING_TIME
    LAST_PING_TIME = time.time() + 15  # Give 15s extra grace period for browser to open
    
    # Abrir o navegador com atraso para garantir que o servidor subiu
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    # Thread secundária roda o servidor
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Thread Principal monitora o Heartbeat
    while True:
        time.sleep(5)
        if time.time() - LAST_PING_TIME > 15:
            print("No heartbeat received for 15s. Shutting down Ghost Process...")
            os._exit(0)

if __name__ == '__main__':
    main()
