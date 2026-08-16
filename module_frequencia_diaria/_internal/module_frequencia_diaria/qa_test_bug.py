import urllib.request
import urllib.parse
import json
from http.cookiejar import CookieJar

def test_bug():
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    urllib.request.install_opener(opener)
    
    # 1. Login
    data = urllib.parse.urlencode({'login': 'QA_Gestor_Test', 'senha': 'qa123'}).encode('utf-8')
    req = urllib.request.Request("http://localhost:5008/login", data=data)
    res = urllib.request.urlopen(req)
    print("Login status:", res.getcode())
    
    # 2. GET /api/acesso-config (This used to destroy the in-memory cache)
    req = urllib.request.Request("http://localhost:5008/api/acesso-config")
    res = urllib.request.urlopen(req)
    config = json.loads(res.read().decode('utf-8'))
    print("GET Config Usuarios Count:", len(config.get('usuarios', [])))
    
    # 3. POST /api/acesso-config (This used to fail with 403 Acesso Negado)
    req = urllib.request.Request("http://localhost:5008/api/acesso-config", data=json.dumps(config).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        res = urllib.request.urlopen(req)
        print("POST Config status:", res.getcode())
        print("BUG FIXED! POST succeeded!")
    except urllib.error.HTTPError as e:
        print("POST Error:", e.code)
        print(e.read().decode('utf-8'))

if __name__ == '__main__':
    test_bug()
