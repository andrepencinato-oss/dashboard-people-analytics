import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDS_PATH = os.path.join('core', 'credentials.json')
TOKEN_PATH = os.path.join('core', 'token.json')

def auth():
    print("Iniciando fluxo de autenticação...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    
    with open(TOKEN_PATH, 'w') as token:
        token.write(creds.to_json())
        
    print("Token atualizado com sucesso!")

if __name__ == '__main__':
    auth()
