import sys
import os
import threading
import time
import subprocess

# ── Configuração de paths ─────────────────────────────────────
if getattr(sys, 'frozen', False):
    app_root = os.path.dirname(sys.executable)
    current_dir = sys._MEIPASS
else:
    app_root = os.path.dirname(os.path.abspath(__file__))
    current_dir = app_root



try:
    log_file = os.path.join(app_root, 'launcher.log')
    try:
        sys.stdout = open(log_file, 'w', encoding='utf-8')
        sys.stderr = sys.stdout
    except Exception:
        pass
    
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    from module_organograma import app_organograma

    def run_app():
        """Executa a função main() do módulo em thread isolada."""
        try:
            app_organograma.main()
        except Exception as e:
            print(f"Erro ao iniciar o modulo Organograma: {e}")

    if __name__ == '__main__':
        print("=== INICIANDO PEOPLE ANALYTICS: MODULO ORGANOGRAMA ===")
        
        # OTA desabilitado para distribuição standalone (exe compilado)
        # O update.zip contém código-fonte Python incompatível com exe onefile
        
        t = threading.Thread(target=run_app, daemon=True)
        t.start()
            
        print("Modulo Organograma (porta 5009) iniciado em background.")
        
        def open_browser():
            import webbrowser
            import urllib.request
            import urllib.error
            url = "http://127.0.0.1:5009/"
            print("Aguardando inicialização do servidor...")
            for _ in range(30):
                try:
                    urllib.request.urlopen(url + "api/status", timeout=1)
                    print("Servidor pronto! Abrindo navegador...")
                    webbrowser.open(url)
                    break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(1)
            else:
                print("Nao foi possivel conectar automaticamente. Acesse manualmente:", url)

        # Inicia a thread que aguarda o servidor e abre o browser
        threading.Thread(target=open_browser, daemon=True).start()
        
        # Mantém o launcher ativo
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Encerrando Módulo Organograma.")
            sys.exit(0)
except Exception as global_e:
    import traceback
    crash_log_path = os.path.join(app_root if 'app_root' in locals() else os.getcwd(), "crash_log.txt")
    with open(crash_log_path, "w") as f:
        f.write(traceback.format_exc())
    raise
