import os
import sys
import io
import json
import glob
import traceback
import csv
import threading
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
core_dir = os.path.join(root_dir, 'core')

if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Pasta de origem dos CSVs (fonte de dados brutos)
DRIVE_FOLDER_ID = '1iH6q59vAFn5Eg1f1b_bkTZMruqd0Uj_c'

# Pasta de banco de dados nuvem (configurações/hierarquias persistidas por cliente)
DRIVE_DB_FOLDER_ID = '1cbtnp4TzKbYK3AJBQT-aXoUuQU6ZQxia'

# Identificador de cliente/tenant (pode ser customizado por instalação)
CLIENT_ID = 'moveis-provincia'

DATA_DIR = os.path.join(current_dir, 'data')

# Arquivos de configuração que devem ser sincronizados com o DB nuvem
CLOUD_SYNC_FILES = [
    'organograma_responsaveis.json',
    'organograma_contagem.json',
    'organograma_posso_contar.json',
    'organograma_movimentacoes.json',
]

def get_drive_service():
    token_path = os.path.join(core_dir, 'token.json')
    token_upload_path = os.path.join(core_dir, 'token_upload.json')
    if os.path.exists(token_upload_path):
        token_path = token_upload_path
    if not os.path.exists(token_path):
        return None
    try:
        creds = Credentials.from_authorized_user_file(token_path)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())
            else:
                return None
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"[DataProcessor] Erro ao criar serviço Drive: {e}")
        return None

def parse_date(d_str):
    if not d_str: return None
    try:
        return datetime.strptime(d_str.strip(), '%d/%m/%Y')
    except:
        return None

def clean_and_title(text):
    if not text: return ""
    import re
    text = text.strip()
    text = re.sub(r'(?i)^(CUSTOS?\s*C/\s*PESSOAL|DESPESAS\s*C/\s*PESSOAL|CUSTO\s*C/\s*PESSOAL)\s*-\s*', '', text)
    words = text.split(' ')
    return ' '.join(w.capitalize() for w in words)

def process_csv_files():
    try:
        print("[Organograma] Processando CSVs baixados de forma estruturada...")
        
        # HEADCOUNT
        headcount_files = glob.glob(os.path.join(DATA_DIR, '*eadcount*.csv')) + glob.glob(os.path.join(DATA_DIR, '*eadcount*.CSV'))
        if headcount_files:
            latest_hc = max(headcount_files, key=os.path.getmtime)
            res_hc = []
            with open(latest_hc, 'r', encoding='ISO-8859-1', errors='replace') as f:
                reader = csv.reader(f, delimiter=',')
                started = False
                for row in reader:
                    if not row: continue
                    if not started:
                        if len(row) > 1 and 'Nome' in row[1]:
                            started = True
                        continue
                    
                    if len(row) >= 8:
                        salario_str = row[4].replace('.', '').replace(',', '.').strip()
                        try:
                            salario = float(salario_str)
                        except:
                            salario = 0.0
                            
                        item = {
                            "cad": row[0].strip(),
                            "nome": clean_and_title(row[1]),
                            "admissao": row[2].strip(),
                            "cargo": clean_and_title(row[3]),
                            "salario": salario,
                            "ccNome": clean_and_title(row[5]),
                            "ccCod": row[7].strip()
                        }
                        if item["cad"] and item["cad"].isdigit():
                            res_hc.append(item)
            
            with open(os.path.join(DATA_DIR, 'headcount.json'), 'w', encoding='utf-8') as f:
                json.dump(res_hc, f, ensure_ascii=False)
            print(f"[Organograma] headcount.json atualizado com {len(res_hc)} registros.")

        # AFASTAMENTOS E METADATA
        afast_files = glob.glob(os.path.join(DATA_DIR, '*fastamento*.csv')) + glob.glob(os.path.join(DATA_DIR, '*fastamento*.CSV'))
        
        metadata = {
            "periodo_headcount": os.path.basename(latest_hc) if 'latest_hc' in locals() else "N/A",
            "periodo_afastamento": "N/A",
            "periodo_inicio": "",
            "periodo_fim": "",
            "atualizado_em": datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        if afast_files:
            latest_af = max(afast_files, key=os.path.getmtime)
            metadata["periodo_afastamento"] = os.path.basename(latest_af)
            
            afast_stats = {}
            afastamentos_por_cad = {}
            
            with open(latest_af, 'r', encoding='ISO-8859-1', errors='replace') as f:
                all_rows = list(csv.reader(f, delimiter=','))
            
            for row in all_rows[:8]:
                clean = [c.strip() for c in row]
                if len(clean) >= 4 and parse_date(clean[1]) and parse_date(clean[3]):
                    metadata["periodo_inicio"] = clean[1]
                    metadata["periodo_fim"] = clean[3]
                    break
            
            started = False
            last_cad = None
            
            for row in all_rows:
                if not row: continue
                
                row_flat = ','.join(row)
                if 'Cadastro' in row_flat and 'Nome' in row_flat:
                    started = True
                    continue
                
                if not started: continue
                
                cad_raw = row[0].strip()
                
                if cad_raw and cad_raw.isdigit() and int(cad_raw) > 100:
                    last_cad = cad_raw
                    data_ini = row[5].strip() if len(row) > 5 else ''
                    sit = row[8].strip() if len(row) > 8 else ''
                    data_fim = row[9].strip() if len(row) > 9 else ''
                else:
                    if not last_cad: continue
                    r = row[:]
                    while r and r[0].strip() == '':
                        r = r[1:]
                    if not r: continue
                    if parse_date(r[0].strip()):
                        data_ini = r[0].strip()
                        sit = r[3].strip() if len(r) > 3 else ''
                        data_fim = r[4].strip() if len(r) > 4 else ''
                    else:
                        continue

                if not last_cad: continue
                
                d = parse_date(data_ini)
                if not d: continue
                
                sit_lower = sit.lower()
                if last_cad not in afast_stats:
                    afast_stats[last_cad] = {"faltas": 0, "atestado": 0, "acidente": 0}
                    
                if 'falta' in sit_lower:
                    afast_stats[last_cad]['faltas'] += 1
                elif 'atestado' in sit_lower:
                    afast_stats[last_cad]['atestado'] += 1
                elif 'acidente' in sit_lower:
                    afast_stats[last_cad]['acidente'] += 1
                
                if last_cad not in afastamentos_por_cad:
                    afastamentos_por_cad[last_cad] = []
                afastamentos_por_cad[last_cad].append({
                    'cad': last_cad,
                    'data': data_ini,
                    'data_obj': d,
                    'situacao': sit,
                    'termino': data_fim
                })
            
            res_af = []
            res_af_hist = []
            
            # Create a lookup for employee data from headcount
            hc_lookup = { item['cad']: item for item in res_hc } if 'res_hc' in locals() else {}
            
            for cad, records in afastamentos_por_cad.items():
                if not records: continue
                
                emp_info = hc_lookup.get(cad, {})
                nome = emp_info.get('nome', 'Desconhecido')
                cargo = emp_info.get('cargo', '')
                ccNome = emp_info.get('ccNome', '')
                
                for r in records:
                    res_af_hist.append({
                        'cad': cad,
                        'nome': nome,
                        'cargo': cargo,
                        'ccNome': ccNome,
                        'data': r['data'],
                        'situacao': r['situacao'],
                        'termino': r['termino']
                    })
                
                latest = max(records, key=lambda x: x['data_obj'])
                res_af.append({
                    'cad': latest['cad'],
                    'data': latest['data'],
                    'situacao': latest['situacao'],
                    'termino': latest['termino']
                })
                
            with open(os.path.join(DATA_DIR, 'afastamentos_historico.json'), 'w', encoding='utf-8') as f:
                json.dump(res_af_hist, f, ensure_ascii=False)
                
            with open(os.path.join(DATA_DIR, 'afastamentos.json'), 'w', encoding='utf-8') as f:
                json.dump(res_af, f, ensure_ascii=False)
                
            with open(os.path.join(DATA_DIR, 'afastamentos_stats.json'), 'w', encoding='utf-8') as f:
                json.dump(afast_stats, f, ensure_ascii=False)
                
            print(f"[Organograma] afastamentos.json atualizado com {len(res_af)} registros recentes.")
            print(f"[Organograma] afastamentos_stats.json atualizado para {len(afast_stats)} funcionarios.")
            print(f"[Organograma] Periodo detectado: {metadata.get('periodo_inicio')} a {metadata.get('periodo_fim')}")
            
        with open(os.path.join(DATA_DIR, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False)
            
    except Exception as e:
        print(f"[Organograma] Erro ao processar CSVs: {e}")
        traceback.print_exc()

# ============================================================
# CLOUD DB SYNC — Lê configurações do DB nuvem (pasta cliente)
# ============================================================

def _get_or_create_client_folder(service):
    """Retorna o ID da subpasta do cliente dentro do DB folder."""
    query = f"'{DRIVE_DB_FOLDER_ID}' in parents and name='{CLIENT_ID}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    # Criar subpasta do cliente
    folder_meta = {
        'name': CLIENT_ID,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [DRIVE_DB_FOLDER_ID]
    }
    folder = service.files().create(body=folder_meta, fields='id').execute()
    print(f"[CloudDB] Subpasta '{CLIENT_ID}' criada no Drive DB.")
    return folder.get('id')

def sync_configs_to_cloud():
    """Faz upload dos arquivos de configuração local para a pasta do cliente no Drive."""
    service = get_drive_service()
    if not service:
        print("[CloudDB] Sem serviço Drive — sync ignorado.")
        return False
    try:
        client_folder_id = _get_or_create_client_folder(service)
        for fname in CLOUD_SYNC_FILES:
            local_path = os.path.join(DATA_DIR, fname)
            if not os.path.exists(local_path):
                continue
            # Check if exists in Drive
            query = f"'{client_folder_id}' in parents and name='{fname}' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            items = results.get('files', [])
            media = MediaFileUpload(local_path, mimetype='application/json', resumable=False)
            if items:
                service.files().update(fileId=items[0]['id'], media_body=media).execute()
            else:
                meta = {'name': fname, 'parents': [client_folder_id]}
                service.files().create(body=meta, media_body=media).execute()
            print(f"[CloudDB] Sincronizado: {fname}")
        return True
    except Exception as e:
        print(f"[CloudDB] Erro ao sincronizar configs: {e}")
        return False

def restore_configs_from_cloud():
    """Baixa arquivos de configuração da pasta do cliente no Drive para local apenas se a nuvem for mais recente."""
    service = get_drive_service()
    if not service:
        return False
    try:
        client_folder_id = _get_or_create_client_folder(service)
        query = f"'{client_folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
        items = results.get('files', [])
        for item in items:
            if item['name'] not in CLOUD_SYNC_FILES:
                continue
            local_path = os.path.join(DATA_DIR, item['name'])
            # Se o arquivo local existe e foi modificado localmente recentemente, preservar a versão local
            if os.path.exists(local_path):
                local_mtime = os.path.getmtime(local_path)
                cloud_mtime_str = item.get('modifiedTime')
                if cloud_mtime_str:
                    try:
                        # Converter timestamp RFC3339 para datetime
                        cloud_dt = datetime.strptime(cloud_mtime_str[:19], "%Y-%m-%dT%H:%M:%S")
                        cloud_mtime = cloud_dt.timestamp()
                        # Se o arquivo local for mais recente (com margem de 10s), manter o local e subir pra nuvem se necessário
                        if local_mtime >= cloud_mtime - 10:
                            print(f"[CloudDB] Mantendo versão local de {item['name']} (mais recente que nuvem)")
                            continue
                    except Exception:
                        pass

            req = service.files().get_media(fileId=item['id'])
            fh = io.FileIO(local_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.close()
            print(f"[CloudDB] Restaurado: {item['name']}")
        return True
    except Exception as e:
        print(f"[CloudDB] Erro ao restaurar configs: {e}")
        return False

def fetch_organograma_data():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Limpa PDFs residuais
        pdf_files = set(glob.glob(os.path.join(DATA_DIR, '*.pdf')) + glob.glob(os.path.join(DATA_DIR, '*.PDF')))
        for pdf in pdf_files:
            try:
                os.remove(pdf)
            except OSError:
                pass
            
        service = get_drive_service()
        if not service:
            print("[Organograma] Aviso: sem autenticação Drive. Rodando com dados locais.")
            return False

        # Restaurar configs do DB nuvem antes de processar
        restore_configs_from_cloud()

        query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType != 'application/vnd.google-apps.folder' and mimeType != 'application/pdf' and trashed = false"
        results = service.files().list(
            q=query,
            orderBy="createdTime desc",
            fields="files(id, name, mimeType)"
        ).execute()

        items = results.get('files', [])
        if not items:
            print("[Organograma] Pasta do Drive vazia ou sem arquivos validos (CSVs).")
            return True
            
        for item in items:
            file_name = item['name']
            if file_name.lower().endswith('.pdf'): continue
            
            file_id = item['id']
            req = service.files().get_media(fileId=file_id)
            file_path = os.path.join(DATA_DIR, file_name)
            
            fh = io.FileIO(file_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.close()
            
            print(f"[Organograma] Arquivo CSV baixado: {file_name}")
            
        process_csv_files()
        return True

    except Exception as e:
        print(f"[Organograma] Falha na sincronizacao do Drive: {e}")
        return False
