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

# ── Configuração de paths ────────────────────────────────────
if getattr(sys, 'frozen', False):
    current_dir = sys._MEIPASS
    app_root = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = current_dir

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

PORT = 5008
URL = f"http://127.0.0.1:{PORT}/dashboard"


def run_server():
    """Importa e inicia apenas o módulo de frequência."""
    try:
        from module_frequencia_diaria import app_frequencia
        app_frequencia.run_server()
    except Exception as e:
        import traceback
        crash_path = os.path.join(app_root, "crash_log.txt")
        with open(crash_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())


def wait_and_open_browser():
    """Aguarda o servidor subir e abre o browser."""
    import urllib.request
    for _ in range(30):          # Tenta por até 15 segundos
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=1)
            webbrowser.open(URL)
            return
        except Exception:
            continue
    # Fallback: tenta abrir mesmo assim
    webbrowser.open(URL)


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
                exe_command = 'start "" "python" "launcher_frequencia.py"'

            bat_content = f"""@echo off
timeout /t 3 /nobreak > nul
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
    # 1. Checar atualizações OTA
    check_ota()

    # 2. Iniciar servidor em thread daemon
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 3. Abrir browser assim que o servidor responder
    browser_thread = threading.Thread(target=wait_and_open_browser, daemon=True)
    browser_thread.start()

    # 4. Manter processo vivo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)
