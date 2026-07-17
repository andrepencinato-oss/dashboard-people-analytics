import sys
import os
import threading
import time

# Set up module path to ensure 'module_people_analytics' and 'core' can be imported 
# if running from source. PyInstaller usually sets everything in _MEIPASS but since 
# we use subfolders, we need to ensure the imports resolve correctly.
if not getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

from module_people_analytics import app_desktop
from module_sst import app_sst
from module_controle_vagas import app_vagas
from module_absenteismo_turnover import app_absenteismo
from module_frequencia_diaria import app_frequencia

def run_app(module):
    """Executa a funo main() do mdulo em thread isolada."""
    try:
        module.main()
    except Exception as e:
        print(f"Erro ao iniciar o modulo {module.__name__}: {e}")

if __name__ == '__main__':
    print("Iniciando Homedock Suite - Shared Core Ecosystem...")
    
    # --- OTA BOOTLOADER ---
    try:
        from core import auto_updater
        import subprocess
        if auto_updater.check_and_download_update():
            print("[OTA BOOTLOADER] Atualizacao pronta na pasta .update_stage/")
            print("[OTA BOOTLOADER] Gerando script de aplicacao...")
            
            bat_path = os.path.join(current_dir, "apply_update.bat")
            bat_content = """@echo off
echo =========================================
echo  HOMEDOCK SUITE - ATUALIZACAO EM ANDAMENTO
echo =========================================
echo Aguardando 3 segundos para fechamento total do Launcher...
timeout /t 3 /nobreak > nul

echo.
echo Copiando novos arquivos...
xcopy /s /y /q ".update_stage\\*" ".\\"

echo.
echo Limpando arquivos temporarios...
rmdir /s /q ".update_stage"

echo.
echo Reiniciando o Launcher...
start "" "python" "main_launcher.py"

echo Atualizacao concluida.
del "%~f0"
"""
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
                
            print("[OTA BOOTLOADER] Iniciando instalador independente e encerrando processo principal...")
            subprocess.Popen([bat_path], cwd=current_dir, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)
    except Exception as e:
        print(f"[OTA BOOTLOADER] Erro ao checar atualizacoes: {e}")
    # ----------------------
    
    modules = [
        app_desktop,
        app_sst,
        app_vagas,
        app_absenteismo,
        app_frequencia
    ]
    
    threads = []
    
    for mod in modules:
        t = threading.Thread(target=run_app, args=(mod,), daemon=True)
        t.start()
        threads.append(t)
        
    print("Todos os modulos foram iniciados em background.")
    
    # Mantm o launcher ativo para que as threads no morram
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando Homedock Suite.")
        sys.exit(0)
