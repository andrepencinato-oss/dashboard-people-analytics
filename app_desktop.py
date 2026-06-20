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
from http.server import BaseHTTPRequestHandler, HTTPServer

DATA_FILE_NAME = 'DP_-_Colaboradores_-_Extrato_Diário.xls'
APP_VERSION = "v1.0.0"

SYNC_FILE_PATH = None
SYNC_ERROR = None

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
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            base_path = get_base_path()
            working_dir = get_working_dir()
            
            global SYNC_FILE_PATH, SYNC_ERROR
            if SYNC_ERROR:
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
                    <div class="traceback">{SYNC_ERROR}</div>
                </body>
                </html>
                """
                self.wfile.write(emergency_html.encode('utf-8'))
                return

            extrato_path = SYNC_FILE_PATH if SYNC_FILE_PATH else os.path.join(working_dir, DATA_FILE_NAME)
            html_template_path = os.path.join(base_path, 'dashboard_dp_colaboradores (1).html')
            
            try:
                data = excel_reader.process_excel_files(extrato_path)
                json_data = json.dumps(data, ensure_ascii=False)
            except Exception as e:
                print(f"Erro ao ler o Excel: {e}")
                try:
                    with open(os.path.join(working_dir, 'leitura_error_log.txt'), 'w', encoding='utf-8') as log_f:
                        log_f.write(traceback.format_exc())
                except Exception:
                    pass
                json_data = "[]"
                
            try:
                with open(html_template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Injetar os dados via Regex
                new_html_content = re.sub(
                    r'const COLAB = \[.*?\];', 
                    f'const COLAB = {json_data};', 
                    html_content, 
                    flags=re.DOTALL
                )

                # Injetar a versão dinamicamente
                new_html_content = new_html_content.replace('{{APP_VERSION}}', APP_VERSION)

                # Injetar script de shutdown antes de fechar a tag body
                shutdown_script = """
<script>
    window.addEventListener('beforeunload', function (e) {
        navigator.sendBeacon('/shutdown');
    });
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
        else:
            self.send_response(404)
            self.end_headers()

def main():
    global SYNC_FILE_PATH, SYNC_ERROR
    try:
        SYNC_FILE_PATH = drive_sync.fetch_latest_excel()
    except Exception as e:
        SYNC_ERROR = str(e)

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
    
    # Abrir o navegador com atraso para garantir que o servidor subiu
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    # Thread Principal roda o servidor, bloqueando e mantendo vivo
    httpd.serve_forever()

if __name__ == '__main__':
    main()
