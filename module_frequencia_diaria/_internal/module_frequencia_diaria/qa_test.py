import urllib.request
import urllib.parse
import json
from http.cookiejar import CookieJar

def test_login():
    print("Iniciando Teste Headless de QA...")
    # Setup de cookies
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    urllib.request.install_opener(opener)
    
    # 1. Testar Rota de Login (GET)
    print("\n[ Passo 1: Acessar Tela de Login ]")
    req = urllib.request.Request("http://localhost:5008/login")
    try:
        res = urllib.request.urlopen(req, timeout=5)
        print(f"Status: {res.getcode()} OK")
    except Exception as e:
        print(f"Erro: {e}")
        return False
        
    # 2. Testar Login (POST)
    print("\n[ Passo 2: Fazer Login (QA_Gestor_Test) ]")
    data = urllib.parse.urlencode({'login': 'QA_Gestor_Test', 'senha': 'qa123'}).encode('utf-8')
    req = urllib.request.Request("http://localhost:5008/login", data=data)
    try:
        res = urllib.request.urlopen(req, timeout=5)
        print(f"Status: {res.getcode()} OK")
        print(f"URL Redirecionada: {res.geturl()}")
        if 'error' in res.geturl():
            print("Falha no login: Credenciais inválidas.")
            return False
        print("Login efetuado com sucesso!")
    except Exception as e:
        print(f"Erro no login: {e}")
        return False

    # 3. Testar Admin (GET)
    print("\n[ Passo 3: Acessar Tela Admin ]")
    req = urllib.request.Request("http://localhost:5008/admin")
    try:
        res = urllib.request.urlopen(req, timeout=5)
        print(f"Status: {res.getcode()} OK")
        html = res.read().decode('utf-8')
        if "Controle de Acesso" in html:
            print("Página Admin carregada corretamente.")
        else:
            print("Conteúdo do Admin não encontrado.")
    except Exception as e:
        print(f"Erro no admin: {e}")
        
    # 4. Status API (GET)
    print("\n[ Passo 4: Verificar API Status ]")
    req = urllib.request.Request("http://localhost:5008/api/status")
    try:
        res = urllib.request.urlopen(req, timeout=5)
        print(f"Status: {res.getcode()} OK")
        print("Servidor está UP.")
    except Exception as e:
        print(f"Erro na API: {e}")
        
    return True

if __name__ == '__main__':
    test_login()
