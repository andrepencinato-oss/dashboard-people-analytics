"""
Launcher dedicado para o módulo Frequência Diária.
- Inicia apenas o servidor de frequência
- Sem terminal visível (console=False no spec)
- Abre o browser automaticamente após o servidor subir
"""
import sys
import os
import threading
import time
import webbrowser
import subprocess

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# ── Configuração de paths ────────────────────────────────────
if getattr(sys, 'frozen', False):
    current_dir = sys._MEIPASS
    app_root = os.path.dirname(sys.executable)
    # No PyInstaller, a raiz do projeto (onde fica 'core') é mapeada para a raiz do _MEIPASS
    project_root = current_dir
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = current_dir
    # A raiz do projeto é a pasta pai
    project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

PORT = 5008
URL = f"http://127.0.0.1:{PORT}/dashboard"


def run_server():
    """Importa e inicia apenas o módulo de frequência."""
    try:
        import app_frequencia
        app_frequencia.run_server()
    except Exception as e:
        import traceback
        crash_path = os.path.join(app_root, "crash_log_server.txt")
        with open(crash_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise

def open_browser_smart(url):
    """Abre o navegador de forma otimizada para ambientes de desktop e servidor RDP/RemoteApp."""
    import subprocess
    
    # 1. Tenta Microsoft Edge em modo App (padrão no Windows Server / RDP)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")
    ]
    for ep in edge_paths:
        if ep and os.path.exists(ep):
            try:
                subprocess.Popen([ep, f"--app={url}"])
                return
            except Exception:
                pass

    # 2. Tenta Google Chrome em modo App
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe")
    ]
    for cp in chrome_paths:
        if cp and os.path.exists(cp):
            try:
                subprocess.Popen([cp, f"--app={url}"])
                return
            except Exception:
                pass

    # 3. Fallback via protocolo do sistema
    try:
        webbrowser.open(url)
    except Exception:
        pass

def wait_and_open_browser():
    """Aguarda o servidor subir e abre o browser de forma resiliente."""
    import urllib.request
    for _ in range(30):          # Tenta por até 15 segundos
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=1)
            open_browser_smart(URL)
            return
        except Exception:
            continue
    # Fallback
    open_browser_smart(URL)


# ── OTA Bootloader ───────────────────────────────────────────
def check_ota():
    try:
        from core import auto_updater
        if auto_updater.check_and_download_update():
            update_stage = os.path.join(app_root, ".update_stage")
            bat_path = os.path.join(app_root, "apply_update.bat")

            if getattr(sys, 'frozen', False):
                exe_command = f'start "" "{os.path.basename(sys.executable)}"'
            else:
                exe_command = 'start "" "python" "module_frequencia_diaria\\launcher.py"'

            bat_content = f"""@echo off
ping 127.0.0.1 -n 4 > nul
xcopy /s /y /q "{update_stage}\\*" "{app_root}\\"
rmdir /s /q "{update_stage}"
cd /d "{app_root}"
{exe_command}
del "%~f0"
"""
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)

            subprocess.Popen(
                [bat_path],
                cwd=app_root,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            sys.exit(0)
    except Exception:
        pass   # OTA falhou silenciosamente, continua a inicialização normal


if __name__ == '__main__':
    try:
        # 1. Checar atualizações OTA
        check_ota()

        # 2. Iniciar servidor em thread daemon
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # 3. Abrir browser assim que o servidor responder
        browser_thread = threading.Thread(target=wait_and_open_browser, daemon=True)
        browser_thread.start()

        # 4. Manter processo vivo
        while True:
            time.sleep(1)
            if not server_thread.is_alive():
                # Se a thread do servidor morrer, encerra o launcher para nao ficar zumbi
                sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        import traceback
        crash_path = os.path.join(app_root, "crash_log_launcher.txt")
        with open(crash_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        sys.exit(1)
