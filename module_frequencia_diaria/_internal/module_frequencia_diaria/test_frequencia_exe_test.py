import subprocess, time, urllib.request, re, sys, os

# Paths (cwd is the locked directory)
EXE_REL_PATH = r'FrequenciaDiaria\FrequenciaDiaria\FrequenciaDiaria.exe'

def kill_existing():
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'FrequenciaDiaria.exe', '/T'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass

def get_exe_path():
    candidates = [
        os.path.join(os.getcwd(), 'FrequenciaDiaria.exe'),
        os.path.join(os.getcwd(), '..', 'FrequenciaDiaria.exe'),
        os.path.join(os.getcwd(), 'FrequenciaDiaria', 'FrequenciaDiaria', 'FrequenciaDiaria.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'FrequenciaDiaria.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'FrequenciaDiaria.exe'),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return None

def launch_exe():
    CREATE_NO_WINDOW = 0x08000000
    exe_path = get_exe_path()
    if not exe_path or not os.path.isfile(exe_path):
        print('EXECUTABLE NOT FOUND', file=sys.stderr)
        sys.exit(1)
    proc = subprocess.Popen([exe_path], creationflags=CREATE_NO_WINDOW)
    return proc

def fetch_html():
    url = 'http://127.0.0.1:5008/dashboard'
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        # try login page as fallback
        try:
            with urllib.request.urlopen('http://127.0.0.1:5008/login', timeout=10) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e2:
            print('ERROR FETCHING HTML:', e2, file=sys.stderr)
            return ''

def extract_version(html):
    # Look for badge-navy class containing version like v2.4.2
    m = re.search(r'badge-navy["\'][^>]*>(v[\d\.]+)<', html)
    if m:
        return m.group(1)
    return None

def main():
    kill_existing()
    proc = launch_exe()
    time.sleep(12)  # wait for server to start
    html = fetch_html()
    version = extract_version(html)
    if version:
        print(f'[Escopo Trancado: Teste executado no caminho /FrequenciaDiaria.exe. Versão capturada na tela: {version}]')
    else:
        print('[Escopo Trancado: Teste executado no caminho /FrequenciaDiaria.exe. Versão capturada na tela: NOT_FOUND]')
    # cleanup
    kill_existing()
    # ensure process terminated
    try:
        proc.terminate()
    except Exception:
        pass

if __name__ == '__main__':
    main()
