import os
import sys
import io
import re
import csv
import json
import time
import datetime
import traceback
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── Resolution of Paths ──────────────────────────────────────────────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = THIS_DIR

# Locate core folder containing token.json / credentials.json
CORE_CANDIDATES = [
    os.path.join(APP_ROOT, 'core'),
    os.path.join(os.path.dirname(APP_ROOT), 'core'),
    r"D:\Projeto geral\People analytics - GP\core"
]

CORE_DIR = None
TOKEN_PATH = None
for c in CORE_CANDIDATES:
    tp = os.path.join(c, 'token.json')
    if os.path.exists(tp):
        CORE_DIR = c
        TOKEN_PATH = tp
        break

if not TOKEN_PATH:
    # Default fallback
    CORE_DIR = os.path.join(APP_ROOT, 'core')
    TOKEN_PATH = os.path.join(CORE_DIR, 'token.json')

DATALAKE_DIR = os.path.join(APP_ROOT, 'data', 'datalake')
os.makedirs(DATALAKE_DIR, exist_ok=True)

DRIVE_FOLDER_ID = '11G8qWpSj87bRo0EmK-JJCFqGQ82MLyRc'


def clean_setor_name(s):
    if not s:
        return s
    s = s.strip()
    if s.upper() in ["TAPEÇARIA GERAL", "TAPEÇARIA COLAGEM"]:
        return "TAPEÇARIA"
    return s


def get_drive_service():
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(f"Google Drive token não encontrado em: {TOKEN_PATH}")

    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)


def read_file_content(service, item):
    if isinstance(item, dict):
        file_id = item['id']
        mime_type = item.get('mimeType', '')
    else:
        file_id = str(item)
        mime_type = ''

    if mime_type.startswith('application/vnd.google-apps.'):
        request = service.files().export_media(fileId=file_id, mimeType='text/csv')
    else:
        request = service.files().get_media(fileId=file_id)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    raw_bytes = fh.getvalue()

    for enc in ['iso-8859-1', 'utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            return raw_bytes.decode(enc)
        except Exception:
            pass
    return raw_bytes.decode('iso-8859-1', errors='replace')


def run_etl():
    print(f"[{datetime.datetime.now()}] Iniciando Motor de ETL Data Lake...")
    print(f"  Diretório Data Lake: {DATALAKE_DIR}")
    print(f"  Token Path: {TOKEN_PATH}")

    service = get_drive_service()

    # List CSV files from Drive folder
    results = service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name, mimeType, modifiedTime, size)",
        pageSize=200
    ).execute()

    items = results.get('files', [])
    print(f"  Encontrados {len(items)} arquivos na pasta do Drive.")

    csv_items = [it for it in items if it['name'].upper().endswith('.CSV')]

    # Separate Headcount vs Frequency reports
    headcount_items = [it for it in csv_items if 'HEAD' in it['name'].upper()]
    frequency_items = [it for it in csv_items if 'HEAD' not in it['name'].upper()]

    # Sort headcount items by modifiedTime
    headcount_items.sort(key=lambda x: x.get('modifiedTime', ''))

    # Deduplicate Headcount Reports by comp
    hc_by_comp = {}
    for item in headcount_items:
        filename = item['name']
        date_match = re.search(r'(\d{2})[-._](\d{2})', filename)
        if date_match:
            comp = f"{date_match.group(1)}-{date_match.group(2)}"
        else:
            comp = item.get('modifiedTime', '')[:7] or time.strftime('%d-%m')
        
        # Always replace with the current item since headcount_items is sorted by modifiedTime (oldest to newest),
        # so the latest modified file for a given comp will be the final one in the dictionary.
        hc_by_comp[comp] = item

    deduped_headcount_items = list(hc_by_comp.values())

    # 1. Process Headcount Reports
    history = {}
    competencias = []

    for item in deduped_headcount_items:
        filename = item['name']
        file_id = item['id']

        date_match = re.search(r'(\d{2})[-._](\d{2})', filename)
        if date_match:
            day, month = date_match.groups()
            comp = f"{day}-{month}"
        else:
            comp = item.get('modifiedTime', '')[:7] or time.strftime('%d-%m')

        try:
            content = read_file_content(service, item)
        except Exception as e:
            print(f"  [AVISO] Falha ao ler arquivo de headcount '{filename}': {e}")
            continue
        lines = content.splitlines()

        hc_by_mat = {}
        hc_by_sector = {}
        total_hc = 0

        reader = csv.reader(lines, delimiter=',')
        for row in reader:
            if not row or len(row) < 6:
                continue
            cad = row[0].strip()
            if re.match(r'^\d{1,6}$', cad):
                raw_setor = row[5].strip()
                setor = clean_setor_name(raw_setor)
                hc_by_mat[cad] = setor
                hc_by_sector[setor] = hc_by_sector.get(setor, 0) + 1
                total_hc += 1

        history[comp] = {
            "by_mat": hc_by_mat,
            "by_sector": hc_by_sector,
            "total": total_hc
        }
        if comp not in competencias:
            competencias.append(comp)

    competencias.sort()
    latest_comp = competencias[-1] if competencias else ""
    latest_headcount = history.get(latest_comp, {"by_mat": {}, "by_sector": {}, "total": 0})

    headcount_history_data = {
        "history": history,
        "competencias": competencias,
        "latest_competencia": latest_comp
    }

    print(f"  Headcount ETL Concluído. Competências: {competencias}, Total Mais Recente ({latest_comp}): {latest_headcount.get('total')}")

    # 2. Process Frequency / Auditoria Reports
    all_records = []
    processed_dates = set()

    # Sort frequency items by modifiedTime
    frequency_items.sort(key=lambda x: x.get('modifiedTime', ''))

    # Deduplicate Frequency Reports by extracted_date
    freq_by_date = {}
    for item in frequency_items:
        filename = item['name']
        date_match = re.search(r'(\d{2}[-._]\d{2})', filename)
        extracted_date = date_match.group(1) if date_match else ''
        if not extracted_date:
            continue
        
        # Always replace with the current item since frequency_items is sorted by modifiedTime
        freq_by_date[extracted_date] = item

    deduped_frequency_items = list(freq_by_date.values())

    for item in deduped_frequency_items:
        filename = item['name']
        file_id = item['id']

        date_match = re.search(r'(\d{2}[-._]\d{2})', filename)
        extracted_date = date_match.group(1) if date_match else ''

        try:
            content = read_file_content(service, item)
        except Exception as e:
            print(f"  [AVISO] Falha ao ler arquivo de frequência '{filename}': {e}")
            continue
        lines = content.splitlines()

        delimiter = ';' if any(';' in line for line in lines[:10]) else ','
        reader = csv.reader(lines, delimiter=delimiter)

        current_setor = "NÃO IDENTIFICADO"
        pending_previsao = ""

        # Check for Period header in early lines
        for line in lines[:5]:
            if 'Período:' in line or 'Periodo:' in line:
                p_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                if p_match:
                    pending_previsao = p_match.group(1)

        for row in reader:
            row = [x.strip() for x in row]
            if not row or not any(row):
                continue
            if row[0].startswith(("Total", "Atrasados", "MOVEIS", "Controle", "Período", "Perodo", "Horário", "Previsto")):
                continue

            matricula_index = -1
            for j in range(min(len(row), 4)):
                if re.match(r'^\d{3,6}$', row[j]):
                    matricula_index = j
                    break

            found_date = ""
            for cell in row:
                if re.match(r'^\d{2}/\d{2}/\d{2,4}$', cell):
                    found_date = cell
                    break

            if matricula_index != -1:
                if matricula_index >= 1:
                    if row[0] and not re.match(r'^\d{2}/\d{2}/\d{2,4}$', row[0]):
                        current_setor = row[0]
                    elif len(row) > 1 and row[1] and not re.match(r'^\d{2}/\d{2}/\d{2,4}$', row[1]):
                        current_setor = row[1]

                previsao = found_date or pending_previsao
                mat_str = row[matricula_index]

                # Match sector with latest headcount by matricula
                official_setor = latest_headcount.get("by_mat", {}).get(mat_str, current_setor)
                official_setor = clean_setor_name(official_setor)

                record = {
                    "setor": official_setor,
                    "local_ponto": clean_setor_name(current_setor),
                    "matricula": mat_str,
                    "nome": row[matricula_index + 1] if len(row) > matricula_index + 1 else "",
                    "hora_prevista": row[matricula_index + 2] if len(row) > matricula_index + 2 else "",
                    "hora_marcacao": row[matricula_index + 3] if len(row) > matricula_index + 3 else "",
                    "situacao": row[matricula_index + 4] if len(row) > matricula_index + 4 else "",
                    "codigo": row[matricula_index + 5] if len(row) > matricula_index + 5 else "",
                    "previsao_termino": previsao,
                    "data_ponto": previsao,
                    "data_relatorio": extracted_date
                }
                all_records.append(record)
                if previsao:
                    processed_dates.add(previsao)
            else:
                possible_setor = ""
                for cell in row:
                    if cell and not re.match(r'^\d{2}/\d{2}/\d{2,4}$', cell):
                        possible_setor = cell
                        break
                if found_date:
                    pending_previsao = found_date

    print(f"  Frequência ETL Concluído. Total de registros sanitizados: {len(all_records)}")

    # 3. Save JSON Files to Data Lake
    frequencia_json_path = os.path.join(DATALAKE_DIR, 'datalake_frequencia.json')
    headcount_json_path = os.path.join(DATALAKE_DIR, 'datalake_headcount.json')
    history_json_path = os.path.join(DATALAKE_DIR, 'datalake_headcount_history.json')
    metadata_json_path = os.path.join(DATALAKE_DIR, 'metadata.json')

    with open(frequencia_json_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    with open(headcount_json_path, 'w', encoding='utf-8') as f:
        json.dump(latest_headcount, f, ensure_ascii=False, indent=2)

    with open(history_json_path, 'w', encoding='utf-8') as f:
        json.dump(headcount_history_data, f, ensure_ascii=False, indent=2)

    metadata = {
        "last_sync": datetime.datetime.now().isoformat(),
        "total_frequencia_records": len(all_records),
        "total_headcount": latest_headcount.get("total", 0),
        "latest_competencia": latest_comp,
        "competencias": competencias,
        "dates_processed": sorted(list(processed_dates))
    }

    with open(metadata_json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.datetime.now()}] Data Lake Atualizado com Sucesso em {DATALAKE_DIR}!")
    return metadata


if __name__ == "__main__":
    try:
        run_etl()
    except Exception as e:
        print(f"ERRO FATAL NO ETL: {e}")
        traceback.print_exc()
        sys.exit(1)
