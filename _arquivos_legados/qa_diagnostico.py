import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Caminhos fixos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, 'core', 'token.json')
CRED_PATH = os.path.join(BASE_DIR, 'core', 'credentials.json')

def forcar_login():
    print(f"Tentando salvar token em: {TOKEN_PATH}")
    if not os.path.exists(os.path.dirname(TOKEN_PATH)):
        os.makedirs(os.path.dirname(TOKEN_PATH))
    
    print(f"Lendo credentials de: {CRED_PATH}")
    if not os.path.exists(CRED_PATH):
        print("FALHA: credentials.json não encontrado!")
        return
        
    flow = InstalledAppFlow.from_client_secrets_file(
        CRED_PATH, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    creds = flow.run_local_server(port=0)
    
    with open(TOKEN_PATH, 'w') as token:
        token.write(creds.to_json())
    print("TOKEN GERADO COM SUCESSO!")

if __name__ == '__main__':
    forcar_login()
