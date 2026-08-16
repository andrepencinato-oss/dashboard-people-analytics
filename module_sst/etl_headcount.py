import os
import io
import json
import traceback
import re
import csv
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Target file and folder IDs
FILE_ID_HEADCOUNT = '1a-OTsyV8e5ynUjJg-1XjMQjV0QpmYSI9'
DEST_FOLDER = '1MMZ363U1ErFlZR-xGI5uDRgzSjUrWM1E'

def get_credentials():
    token_path = r'D:\Projeto geral\People analytics - GP\core\token.json'
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"Credenciais não encontradas em {token_path}")
    return Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive'])

def download_headcount_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()

def calculate_tempo_empresa(admissao_str, reference_date=None):
    if reference_date is None:
        reference_date = datetime.now()
    try:
        adm_date = datetime.strptime(admissao_str, '%d/%m/%Y')
        months = (reference_date.year - adm_date.year) * 12 + (reference_date.month - adm_date.month)
        if reference_date.day < adm_date.day and months > 0:
            months -= 1
        years = round(months / 12, 1)
        
        y_int = months // 12
        m_int = months % 12
        if y_int > 0 and m_int > 0:
            tempo_str = f"{y_int} ano(s) e {m_int} mês(es)"
        elif y_int > 0:
            tempo_str = f"{y_int} ano(s)"
        else:
            tempo_str = f"{m_int} mês(es)"
            
        return {
            "tempo_empresa_meses": months,
            "tempo_empresa_anos": years,
            "tempo_empresa_str": tempo_str,
            "tempo_empresa": years
        }
    except Exception:
        return {
            "tempo_empresa_meses": 0,
            "tempo_empresa_anos": 0.0,
            "tempo_empresa_str": "—",
            "tempo_empresa": 0.0
        }

def clean_sector_name(setor_str):
    if not setor_str:
        return "GERAL"
    s = str(setor_str).strip()
    s = re.sub(r'^(?:CUSTOS?|DESPESAS?)\s+C/\s+PESSOAL\s+-\s+', '', s, flags=re.IGNORECASE)
    return s.strip() or "GERAL"

def parse_salary(salario_str):
    if not salario_str:
        return 0.0
    try:
        s = str(salario_str).strip().replace('.', '').replace(',', '.')
        return float(s)
    except Exception:
        return 0.0

def parse_headcount_data(raw_bytes):
    try:
        content_text = raw_bytes.decode('latin1')
    except Exception:
        content_text = raw_bytes.decode('utf-8', errors='replace')
        
    lines = content_text.splitlines()
    
    # 1. Identificar dinamicamente a linha de cabeçalho correta (skiprows)
    header_idx = -1
    for idx, l in enumerate(lines):
        if "Nome" in l and "Admissão" in l:
            header_idx = idx
            break
            
    if header_idx == -1:
        raise ValueError("Linha de cabeçalho contendo 'Nome' e 'Admissão' não foi encontrada.")
        
    reader = csv.reader(lines[header_idx:])
    headers = [h.strip() for h in next(reader)]
    
    colaboradores = []
    for row in reader:
        if len(row) < 6:
            continue
        cad = row[0].strip()
        nome = row[1].strip()
        admissao = row[2].strip()
        cargo = row[3].strip()
        salario_raw = row[4].strip() if len(row) > 4 else ""
        setor = clean_sector_name(row[5].strip() if len(row) > 5 else "GERAL")
        
        # Filtra apenas linhas válidas de funcionário (com data de admissão dd/mm/yyyy)
        if re.match(r'^\d{2}/\d{2}/\d{4}$', admissao):
            salario_val = parse_salary(salario_raw)
            tempo_info = calculate_tempo_empresa(admissao)
            colaboradores.append({
                "cad": cad,
                "nome": nome,
                "admissao": admissao,
                "cargo": cargo,
                "salario": salario_val,
                "setor": setor,
                "area": setor,
                "tempo_empresa_meses": tempo_info["tempo_empresa_meses"],
                "tempo_empresa_anos": tempo_info["tempo_empresa_anos"],
                "tempo_empresa_str": tempo_info["tempo_empresa_str"],
                "tempo_empresa": tempo_info["tempo_empresa"]
            })
            
    # 2. Gerar consolidação de indicadores por Área/Setor
    area_dict = {}
    total_headcount = len(colaboradores)
    
    for c in colaboradores:
        a = c["area"]
        if a not in area_dict:
            area_dict[a] = {
                "area": a,
                "setor": a,
                "total_colaboradores": 0,
                "soma_meses": 0,
                "soma_anos": 0.0,
                "soma_salario": 0.0
            }
        area_dict[a]["total_colaboradores"] += 1
        area_dict[a]["soma_meses"] += c["tempo_empresa_meses"]
        area_dict[a]["soma_anos"] += c["tempo_empresa_anos"]
        area_dict[a]["soma_salario"] += c["salario"]
        
    indicadores_por_area = []
    for a, item in area_dict.items():
        count = item["total_colaboradores"]
        pct = round((count / total_headcount) * 100, 2) if total_headcount > 0 else 0.0
        avg_meses = round(item["soma_meses"] / count, 1) if count > 0 else 0.0
        avg_anos = round(item["soma_anos"] / count, 1) if count > 0 else 0.0
        avg_sal = round(item["soma_salario"] / count, 2) if count > 0 else 0.0
        
        indicadores_por_area.append({
            "area": a,
            "setor": a,
            "total_colaboradores": count,
            "headcount": count,
            "percentual": pct,
            "tempo_empresa_medio_meses": avg_meses,
            "tempo_empresa_medio_anos": avg_anos,
            "salario_medio": avg_sal,
            "folha_total": round(item["soma_salario"], 2)
        })
        
    indicadores_por_area.sort(key=lambda x: x["total_colaboradores"], reverse=True)
    
    # 3. Indicadores Gerais
    soma_geral_meses = sum(c["tempo_empresa_meses"] for c in colaboradores)
    soma_geral_anos = sum(c["tempo_empresa_anos"] for c in colaboradores)
    avg_geral_meses = round(soma_geral_meses / total_headcount, 1) if total_headcount > 0 else 0.0
    avg_geral_anos = round(soma_geral_anos / total_headcount, 1) if total_headcount > 0 else 0.0
    
    indicadores_gerais = {
        "total_colaboradores": total_headcount,
        "total_areas": len(indicadores_por_area),
        "tempo_empresa_medio_meses": avg_geral_meses,
        "tempo_empresa_medio_anos": avg_geral_anos
    }
    
    payload = {
        "atualizado_em": datetime.now().isoformat(),
        "total_headcount": total_headcount,
        "indicadores_gerais": indicadores_gerais,
        "indicadores_por_area": indicadores_por_area,
        "colaboradores": colaboradores
    }
    
    return payload

def run_etl():
    try:
        print("Iniciando ETL de Headcount...")
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        # 1. Ler arquivo do Drive
        print(f"Baixando arquivo principal de Headcount ID: {FILE_ID_HEADCOUNT}...")
        raw_bytes = download_headcount_file(service, FILE_ID_HEADCOUNT)
        
        # 2. Processar e limpar dados
        payload = parse_headcount_data(raw_bytes)
        print(f"Dados processados com sucesso. Total de colaboradores: {payload['total_headcount']} em {payload['indicadores_gerais']['total_areas']} áreas.")
        
        # 3. Gerar payload JS global
        js_str = f"window.__HEADCOUNT_DATA__ = {json.dumps(payload, ensure_ascii=False, indent=2)};"
        
        # Salvar localmente
        local_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(local_dir, 'headcount_data.js')
        with open(local_path, 'w', encoding='utf-8') as fp:
            fp.write(js_str)
        print(f"Arquivo local salvo com sucesso em: {local_path}")
        
        # 4. Upload para Google Drive (Destino) como headcount_data.js
        q_exist = f"name='headcount_data.js' and '{DEST_FOLDER}' in parents and trashed = false"
        exist_res = service.files().list(q=q_exist).execute().get('files', [])
        
        media = MediaIoBaseUpload(io.BytesIO(js_str.encode('utf-8')), mimetype='application/javascript', resumable=True)
        if exist_res:
            file_id = exist_res[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"Arquivo headcount_data.js (ID: {file_id}) atualizado no Google Drive.")
        else:
            file_metadata = {
                'name': 'headcount_data.js',
                'parents': [DEST_FOLDER]
            }
            res = service.files().create(body=file_metadata, media_body=media).execute()
            print(f"Arquivo headcount_data.js criado no Google Drive (ID: {res.get('id')}).")
            
        print("ETL concluído com sucesso!")
        return True
    except Exception as e:
        print(f"Erro no ETL de Headcount: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    run_etl()
