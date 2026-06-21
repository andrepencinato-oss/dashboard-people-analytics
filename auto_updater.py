import urllib.request
import urllib.error
import json
import os
import sys
import subprocess
import time

GITHUB_REPO = "andrepencinato-oss/dashboard-people-analytics"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def _parse_version(version_str):
    # e.g., "v2.0.0" -> (2, 0, 0)
    version_str = version_str.lower().replace('v', '').strip()
    parts = version_str.split('.')
    try:
        return tuple(map(int, parts))
    except ValueError:
        return (0, 0, 0)

def check_and_apply_updates(current_version):
    """
    Verifica se há versão mais recente no GitHub Releases e aplica o update se existir.
    """
    print(f"Verificando atualizações. Versão atual: {current_version}...")
    try:
        # 1. Obter info da última release
        req = urllib.request.Request(API_URL, headers={'User-Agent': 'AutoUpdater'})
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print("Não foi possível acessar a API do GitHub.")
                return False
            data = json.loads(response.read().decode('utf-8'))
        
        latest_version = data.get('tag_name', '')
        if not latest_version:
            return False
            
        current_tuple = _parse_version(current_version)
        latest_tuple = _parse_version(latest_version)
        
        print(f"Versão no GitHub: {latest_version}")
        
        if latest_tuple > current_tuple:
            print("Atualização disponível! Preparando download...")
            
            # Encontrar o asset correspondente ao app_desktop.exe
            download_url = None
            for asset in data.get('assets', []):
                if asset['name'] == 'app_desktop.exe':
                    download_url = asset['browser_download_url']
                    break
            
            if not download_url:
                print("Nenhum executável (app_desktop.exe) encontrado na Release.")
                return False
                
            # 2. Download do novo arquivo
            new_exe_path = "app_desktop_update.exe"
            print(f"Baixando nova versão de {download_url}...")
            
            # Se já existir um arquivo temporário, remova-o
            if os.path.exists(new_exe_path):
                os.remove(new_exe_path)
                
            urllib.request.urlretrieve(download_url, new_exe_path)
            
            print("Download concluído. Reiniciando para aplicar a atualização...")
            
            # 3. Hot-swap usando um arquivo batch
            bat_path = "apply_update.bat"
            # O script bat aguarda 2 segundos, substitui o arquivo original e o abre novamente
            bat_content = f"""@echo off
echo Atualizando o sistema... Por favor aguarde.
timeout /t 3 /nobreak > nul
move /y {new_exe_path} app_desktop.exe
start app_desktop.exe
del "%~f0"
"""
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
                
            # Executa o batch sem bloquear e fecha o programa atual
            subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)
        else:
            print("O sistema já está na versão mais recente.")
            return False
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("Nenhuma Release encontrada no repositório.")
        else:
            print(f"Erro HTTP ao verificar atualização: {e}")
    except Exception as e:
        print(f"Falha ao verificar/aplicar atualizações: {e}")
    
    return False

if __name__ == "__main__":
    check_and_apply_updates("v1.0.0")
