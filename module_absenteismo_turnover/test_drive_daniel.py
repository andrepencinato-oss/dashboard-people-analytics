import os
import io
import re
import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

BASE_DIR = r'D:\Projeto geral\People analytics - GP'
TOKEN_PATH = os.path.join(BASE_DIR, 'core', 'token.json')
SCOPES = ['https://www.googleapis.com/auth/drive']

FILE_ID = '1hSzhEd2VudRnKdvkoTbVJOO7LhxtMuyQ'

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_path = os.path.join(BASE_DIR, 'core', 'credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

def download_file_from_drive(file_id, output_path):
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(output_path, mode='wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    print("Baixando do Drive...")
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")
    fh.close()
    return output_path

def process_and_filter(file_path, cod_target="560", sit_target="101"):
    df = pd.read_excel(file_path, engine='xlrd')
    df = df.fillna('')

    current_cod = ""
    current_nome = ""
    current_escala_raw = ""
    current_escala_times = ""

    results = []
    total_minutes = 0

    for index, row in df.iterrows():
        col0 = str(row.iloc[0]).strip()
        col1 = str(row.iloc[1]).strip()
        col2 = str(row.iloc[2]).strip()
        col3 = str(row.iloc[3]).strip()
        col4 = str(row.iloc[4]).strip()
        col5 = str(row.iloc[5]).strip() if len(row) > 5 else ""

        if not col0:
            continue

        if col0.isdigit() and col1 != "" and col2 == "" and "Total" not in col0:
            current_cod = col0
            current_nome = col1
            continue

        if col0.isdigit() and col3 != "" and ":" in col3 and len(col3.split()) >= 2 and col4 == "":
            current_escala_raw = col0.zfill(4)
            current_escala_times = col3
            continue

        if len(col0) == 8 and col0.count('/') == 2:
            data = col0
            dia = col1
            marcacoes_raw = col2
            sit_cod = col3
            sit_desc = col4
            horas = col5
            
            if current_cod == cod_target and str(sit_target) in sit_cod:
                escala_parts = current_escala_times.split()
                if len(escala_parts) == 4:
                    escala_str = f"{current_escala_raw} entrada {escala_parts[0]} almoço {escala_parts[1]} às {escala_parts[2]} saída {escala_parts[3]}"
                elif len(escala_parts) == 2:
                    escala_str = f"{current_escala_raw} entrada {escala_parts[0]} saída {escala_parts[1]}"
                else:
                    escala_str = f"{current_escala_raw} {current_escala_times}"

                marc_parts = marcacoes_raw.split()
                if len(marc_parts) == 4:
                    marc_str = f"entrada {marc_parts[0]} almoço {marc_parts[1]} {marc_parts[2]} saída {marc_parts[3]}"
                elif len(marc_parts) == 3:
                     marc_str = f"entrada {marc_parts[0]} almoço {marc_parts[1]} {marc_parts[2]} saída Não marcou"
                elif len(marc_parts) == 2:
                    marc_str = f"entrada {marc_parts[0]} saída {marc_parts[1]}"
                elif len(marc_parts) == 1:
                    marc_str = f"entrada {marc_parts[0]}"
                elif len(marc_parts) == 0:
                    marc_str = "Não marcou"
                else:
                    marc_str = " ".join(marc_parts)

                block = (
                    f"data {data}\n"
                    f"Dia: {dia}\n"
                    f"Cod. {current_cod}\n"
                    f"Nome: {current_nome}\n"
                    f"Escala: {escala_str}\n"
                    f"Marcação: {marc_str}\n"
                    f"Situação Apurada: {sit_cod} {sit_desc}\n"
                    f"Horas: {horas}"
                )
                results.append(block)
                
                # Parse hours
                match = re.search(r"(\d{2,3}):(\d{2})", horas)
                if match:
                    h = int(match.group(1))
                    m = int(match.group(2))
                    total_minutes += (h * 60) + m

    return results, total_minutes

if __name__ == "__main__":
    local_file = os.path.join(BASE_DIR, 'module_absenteismo_turnover', 'downloaded_abs.xls')
    try:
        download_file_from_drive(FILE_ID, local_file)
        results, total_minutes = process_and_filter(local_file, cod_target="560", sit_target="101")
        
        print("--- RESULTADOS DANIEL (560) - 101 ---")
        for r in results:
            print(r)
            print("-" * 20)
            
        hours = total_minutes // 60
        minutes = total_minutes % 60
        print(f"\nTotal de registros encontrados: {len(results)}")
        print(f"Total de horas somadas: {hours:02d}:{minutes:02d}")
    except Exception as e:
        print(f"Erro: {e}")
