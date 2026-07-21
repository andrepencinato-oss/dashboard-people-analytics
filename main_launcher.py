import sys
import os
import threading
import time
import subprocess

if getattr(sys, 'frozen', False):
    current_dir = sys._MEIPASS
    app_root = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = current_dir

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from module_people_analytics import app_desktop
    from module_sst import app_sst
    from module_controle_vagas import app_vagas
    from module_absenteismo_turnover import app_absenteismo
    from module_frequencia_diaria import app_frequencia
    from module_organograma import app_organograma

    def run_app(module):
        """Executa a função main() do módulo em thread isolada."""
        try:
            module.main()
        except Exception as e:
            print(f"Erro ao iniciar o modulo {module.__name__}: {e}")

    if __name__ == '__main__':
        print("Iniciando People Analytics Frequencia Diaria...")
        
        # --- OTA BOOTLOADER ---
        try:
            from core import auto_updater
            if auto_updater.check_and_download_update():
                print("[OTA BOOTLOADER] Atualizacao pronta na pasta .update_stage/")
                print("[OTA BOOTLOADER] Gerando script de aplicacao...")
                
                update_stage = os.path.join(app_root, ".update_stage")
                bat_path = os.path.join(app_root, "apply_update.bat")
                
                exe_command = f'start "" "{os.path.basename(sys.executable)}"' if getattr(sys, 'frozen', False) else 'start "" "python" "main_launcher.py"'
                
                bat_content = f"""@echo off
echo =========================================
echo  PEOPLE ANALYTICS - ATUALIZACAO EM ANDAMENTO
echo =========================================
echo Aguardando 3 segundos para fechamento total do sistema...
timeout /t 3 /nobreak > nul

echo.
echo Copiando novos arquivos...
xcopy /s /y /q "{update_stage}\\*" "{app_root}\\"

echo.
echo Limpando arquivos temporarios...
rmdir /s /q "{update_stage}"

echo.
echo Reiniciando o sistema...
cd /d "{app_root}"
{exe_command}

echo Atualizacao concluida.
del "%~f0"
"""
                with open(bat_path, 'w', encoding='utf-8') as f:
                    f.write(bat_content)
                    
                print("[OTA BOOTLOADER] Iniciando instalador independente e encerrando processo principal...")
                subprocess.Popen([bat_path], cwd=app_root, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                sys.exit(0)
        except Exception as e:
            print(f"[OTA BOOTLOADER] Erro ao checar atualizacoes: {e}")
        # ----------------------
        
        modules = [
            app_desktop,
            app_sst,
            app_vagas,
            app_absenteismo,
            app_frequencia,
            app_organograma
        ]
        
        threads = []
        
        for mod in modules:
            t = threading.Thread(target=run_app, args=(mod,), daemon=True)
            t.start()
            threads.append(t)
            
        print("Todos os modulos foram iniciados em background.")
        
        # Mantém o launcher ativo
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Encerrando People Analytics Frequencia Diaria.")
            sys.exit(0)
except Exception as global_e:
    import traceback
    crash_log_path = os.path.join(app_root if 'app_root' in locals() else os.getcwd(), "crash_log.txt")
    with open(crash_log_path, "w") as f:
        f.write(traceback.format_exc())
    raise
