import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.readonly']
DOCUMENT_ID = '1X7E-BD8cGCHY3HNzTs7PN4LIr0nfUJwOJIO5YFzonB4'

def get_docs_text(service):
    doc = service.documents().get(documentId=DOCUMENT_ID).execute()
    content = doc.get('body').get('content')
    text = ""
    for el in content:
        if 'paragraph' in el:
            elements = el.get('paragraph').get('elements')
            for elem in elements:
                if 'textRun' in elem:
                    text += elem.get('textRun').get('content')
    return text

def analyze_sheet(path):
    df = pd.read_html(path, decimal=',', thousands='.', match='CADASTRO')[0]
    df = df.dropna(subset=['CADASTRO', 'NOME'])
    
    inconsistencies = {'cargo': [], 'salario': [], 'setor': []}
    
    for (cad, nome), group in df.groupby(['CADASTRO', 'NOME']):
        # Check CARGO
        if 'CARGO' in group.columns:
            cargos = group['CARGO'].dropna().unique()
            if len(cargos) > 1:
                inconsistencies['cargo'].append(f"{int(cad)} {nome} - {', '.join([str(c) for c in cargos])}")
                
        # Check SALARIO
        if 'SALARIO' in group.columns:
            salarios = group['SALARIO'].dropna().unique()
            if len(salarios) > 1:
                inconsistencies['salario'].append(f"{int(cad)} {nome} - {', '.join([str(s) for s in salarios])}")
            elif len(salarios) == 1 and (salarios[0] == 0 or salarios[0] == '0' or salarios[0] == '0,00' or salarios[0] == 0.0):
                inconsistencies['salario'].append(f"{int(cad)} {nome} - ZERADO (0.00)")
                
        # Check CENTRO_CUSTO
        if 'CENTRO_CUSTO' in group.columns:
            setores = group['CENTRO_CUSTO'].dropna().unique()
            if len(setores) > 1:
                inconsistencies['setor'].append(f"{int(cad)} {nome} - {', '.join([str(s) for s in setores])}")

    return inconsistencies

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('docs', 'v1', credentials=creds)

    print("Fetching current doc format...")
    print(get_docs_text(service)[:1000]) # Print first 1000 chars to see formatting
    
    print("\\nAnalyzing Extrato Diario...")
    inc_extrato = analyze_sheet('DP_-_Colaboradores_-_Extrato_Diário.xls')
    print("Cargo Extrato:", len(inc_extrato['cargo']), inc_extrato['cargo'][:3])
    print("Salario Extrato:", len(inc_extrato['salario']), inc_extrato['salario'][:3])
    print("Setor Extrato:", len(inc_extrato['setor']), inc_extrato['setor'][:3])
    
    print("\\nAnalyzing Listagem Detalhada...")
    inc_lista = analyze_sheet('DP_-_Colaboradores_-_Listagem_detalhada_de_eventos_e_notificações.xls')
    print("Cargo Lista:", len(inc_lista['cargo']), inc_lista['cargo'][:3])
    print("Salario Lista:", len(inc_lista['salario']), inc_lista['salario'][:3])
    print("Setor Lista:", len(inc_lista['setor']), inc_lista['setor'][:3])

if __name__ == '__main__':
    main()
