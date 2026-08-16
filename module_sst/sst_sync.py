import os
import io
import json
import traceback
import re
import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Target folder IDs
SOURCE_FOLDER = '1JkjIm64E-uXmyzMoRmKMPXtXh3Btx84l'
DEST_FOLDER = '1MMZ363U1ErFlZR-xGI5uDRgzSjUrWM1E'

def get_credentials():
    token_path = r'D:\Projeto geral\People analytics - GP\core\token.json'
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"Credenciais não encontradas em {token_path}")
    return Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive'])

def find_file_in_drive(service, name_contains):
    query = f"name contains '{name_contains}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    if files:
        # Pega o mais recente
        return files[0]
    return None

def download_dataframe(service, file_id, mime_type, filename):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    
    if mime_type == 'text/csv' or filename.lower().endswith('.csv'):
        try:
            # skiprows=3 para pular os cabeçalhos sujos do sistema (geralmente as 3 primeiras linhas)
            df = pd.read_csv(fh, skiprows=3, sep=';', encoding='latin1', on_bad_lines='skip')
        except:
            fh.seek(0)
            df = pd.read_csv(fh, skiprows=3, sep=',', encoding='utf-8', on_bad_lines='skip')
    else:
        # Excel
        try:
            df = pd.read_excel(fh, skiprows=1) # No excel Dias Perdidos/Frequencia o titulo ta na 1a linha
        except Exception:
            fh.seek(0)
            df = pd.read_excel(fh)
    
    return df

import csv

def parse_afastados(raw_records):
    parsed = []
    seen_ids = set()
    for row in raw_records:
        line_str = " ".join([str(v) for v in row.values() if v is not None])
        for parts in csv.reader([line_str]):
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 5 and parts[0].isdigit() and len(parts[0]) >= 3:
                emp_id = int(parts[0])
                if emp_id not in seen_ids:
                    seen_ids.add(emp_id)
                    nome = parts[1]
                    setor = parts[3] if len(parts) > 3 else "-"
                    motivo = "Auxílio Doença"
                    inicio = "-"
                    fim = "-"
                    dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', line_str)
                    if len(dates) >= 2:
                        inicio = dates[-2]
                        fim = dates[-1]
                    elif len(dates) == 1:
                        inicio = dates[0]
                    for keyword in ["Auxílio Doença", "Auxilio Doenca", "Licença Maternidade", "Licenca Maternidade", "Acidente de Trabalho", "Acidente"]:
                        if keyword.lower() in line_str.lower():
                            motivo = keyword
                            break
                    parsed.append({
                        "id": emp_id,
                        "nome": nome,
                        "setor": setor,
                        "motivo": motivo,
                        "inicio": inicio,
                        "fim": fim
                    })
    return parsed

def parse_acidentes(raw_records):
    parsed = []
    current_tipo = "Típico"
    for row in raw_records:
        line_str = " ".join([str(v) for v in row.values() if v is not None])
        for parts in csv.reader([line_str]):
            parts = [p.strip() for p in parts if p.strip()]
            if any("TRAJETO" in p.upper() for p in parts):
                current_tipo = "Trajeto"
            elif any("TIPICO" in p.upper() or "TÍPICO" in p.upper() for p in parts):
                current_tipo = "Típico"
            
            if len(parts) >= 6 and re.match(r'^\d{2}/\d{2}/\d{4}$', parts[0]):
                data_aci = parts[0]
                emp_id_str = parts[4] if len(parts) > 4 else ""
                nome = parts[5] if len(parts) > 5 else ""
                afastamento = parts[6] if len(parts) > 6 else ""
                dias = 0
                if afastamento and afastamento != "00/00/0000":
                    dias = 15
                if emp_id_str.isdigit():
                    desc_lower = line_str.lower()
                    parte = "Membros Superiores (Mãos/Dedos)"
                    if any(w in desc_lower for w in ["pé", "pe", "perna", "tornozelo", "joelho", "calcanhar"]):
                        parte = "Membros Inferiores (Pés/Pernas)"
                    elif any(w in desc_lower for w in ["olho", "cabeça", "rosto", "face", "ouvido"]):
                        parte = "Cabeça / Olhos"
                    elif any(w in desc_lower for w in ["coluna", "costas", "lombar", "tronco"]):
                        parte = "Tronco / Coluna"

                    lesao = "Contusão / Impacto"
                    if any(w in desc_lower for w in ["corte", "cortou", "ferimento", "feriu", "lacer"]):
                        lesao = "Corte / Ferimento"
                    elif any(w in desc_lower for w in ["fratura", "quebr", "trinc"]):
                        lesao = "Fratura"
                    elif any(w in desc_lower for w in ["torc", "tors", "entors"]):
                        lesao = "Torção / Entorse"
                    elif any(w in desc_lower for w in ["queimadura", "queim"]):
                        lesao = "Queimadura"

                    parsed.append({
                        "data": data_aci[:5],
                        "data_full": data_aci,
                        "id": int(emp_id_str),
                        "colaborador": nome,
                        "setor": "PRODUÇÃO",
                        "tipo": current_tipo,
                        "causa": "Acidente registrado",
                        "parte": parte,
                        "lesao": lesao,
                        "dias": dias
                    })
    return parsed

CID_DESCRIPTIONS = {
    "Z01.4": "Exame ginecológico (geral) (de rotina)",
    "Z00.0": "Exame médico geral",
    "Z50.1": "Outras fisioterapias",
    "M54.5": "Dor lombar baixa",
    "M54.4": "Lumbago com ciática",
    "M54.2": "Cervicalgia",
    "M54.0": "Dorsalgia",
    "M79.6": "Dor em membro",
    "M79.1": "Mialgia",
    "M25.5": "Dor articular",
    "M25.0": "Hemartrose",
    "M19.0": "Artrose primária de outras articulações",
    "S72.0": "Fratura do colo do fêmur",
    "S55.1": "Traumatismo da artéria radial ao nível do antebraço",
    "R10.0": "Dor abdominal aguda",
    "R10.4": "Outras dores abdominais e as não especificadas",
    "R07.0": "Dor de garganta",
    "J06.9": "Infecção aguda das vias aéreas superiores não especificada",
    "J00.0": "Nasofaringite aguda (resfriado comum)",
    "J03.9": "Amigdalite aguda não especificada",
    "J11.0": "Influenza (gripe) devida a vírus não identificado",
    "A09.0": "Diarréia e gastroenterite de origem infecciosa presumível",
    "F41.1": "Ansiedade generalizada",
    "F32.0": "Episódio depressivo leve",
    "H10.0": "Conjuntivite mucopurulenta",
    "H10.3": "Conjuntivite aguda não especificada",
    "I84.5": "Hemorróidas externas sem menção de complicação",
    "N23.0": "Cólica nefrética não especificada",
    "N39.0": "Infecção do trato urinário de localização não especificada",
    "L02.9": "Abscesso cutâneo, furúnculo e antraz de localização não especificada"
}

def parse_atestados(raw_records):
    parsed = []
    current_nome = ""
    current_setor = "GERAL"
    
    for row in raw_records:
        line_str = " ".join([str(v) for v in row.values() if v is not None])
        for parts in csv.reader([line_str]):
            parts = [p.strip() for p in parts if p.strip()]
            
            for idx, p in enumerate(parts):
                if p == "Local:" or "Local:" in p:
                    if len(p) > 6:
                        current_setor = p.replace("Local:", "").strip()
                    elif len(parts) > idx + 1:
                        for next_p in parts[idx+1:]:
                            if next_p and next_p.strip():
                                current_setor = next_p.strip()
                                break
                    break
                elif re.match(r'^\d+(\.\d+)+\s*-\s*', p):
                    current_setor = p
                    break
            
            if len(parts) >= 2 and ("Nome:" in parts[0] or "Nome" in parts[0]):
                current_nome = parts[1] if len(parts) > 1 else ""
            
            if any(kw in line_str for kw in ["Empresa:", "Período Início", "Início,Término", "Dt Admissão", "Dt Nascimento", "Período Fim", "SMMC103"]):
                continue

            dates = []
            for p in parts:
                m = re.match(r'^(\d{2})/(\d{2})/(\d{2}|\d{4})$', p)
                if m:
                    d, m_val, y = m.group(1), m.group(2), m.group(3)
                    if len(y) == 2:
                        y = "20" + y
                    dates.append(f"{d}/{m_val}/{y}")
            
            if len(dates) >= 1:
                inicio = dates[0]
                termino = dates[1] if len(dates) >= 2 else dates[0]
                
                cid = "-"
                cid_idx = -1
                for idx, p in enumerate(parts):
                    if re.match(r'^[A-Z]\d{2}(\.\d)?$', p):
                        cid = p
                        cid_idx = idx
                        break
                
                if cid_idx == -1:
                    continue
                
                colab = ""
                if cid_idx > 0 and len(parts[cid_idx-1]) > 3 and not parts[cid_idx-1].isdigit() and parts[cid_idx-1] != "Externo":
                    colab = parts[cid_idx-1]
                elif current_nome:
                    colab = current_nome
                else:
                    colab = "—"
                
                ocorrencia = "-"
                descricao = "-"
                if len(parts) > cid_idx + 1:
                    ocorrencia = parts[cid_idx + 1]
                    if len(parts) > cid_idx + 2 and not parts[cid_idx + 2].isdigit() and not parts[cid_idx + 2].startswith("000"):
                        descricao = parts[cid_idx + 1]
                        ocorrencia = parts[cid_idx + 2]
                
                if descricao == "-" or descricao == "":
                    descricao = CID_DESCRIPTIONS.get(cid, ocorrencia if ocorrencia != "-" else f"CID {cid}")
                
                duracao = "-"
                dias_num = 1
                for idx, p in enumerate(parts):
                    m = re.match(r'^(\d+(?:[,.]\d+)?|\d{2}:\d{2})\s+(Hr\(s\)|Dia\(s\)|Hr|Dia|Dias|Hrs)$', p, re.IGNORECASE)
                    if m:
                        duracao = p
                        if "dia" in m.group(2).lower():
                            try:
                                dias_num = int(float(m.group(1).replace(',', '.')))
                            except:
                                dias_num = 1
                        else:
                            dias_num = 1
                        break
                    elif p in ["Hr(s)", "Dia(s)", "Hr", "Dia", "Dias", "Hrs"]:
                        val = ""
                        for j in range(idx - 1, -1, -1):
                            if parts[j] and (re.match(r'^\d+([,.]\d+)?$', parts[j]) or re.match(r'^\d{2}:\d{2}$', parts[j])):
                                val = parts[j]
                                break
                        if val:
                            duracao = f"{val} {p}"
                            if "Dia" in p:
                                try:
                                    dias_num = int(float(val.replace(',', '.')))
                                except:
                                    dias_num = 1
                            else:
                                dias_num = 1
                        break
                
                if colab and colab != "—":
                    if not any(x['colaborador'] == colab and x['inicio'] == inicio and x['termino'] == termino and x['cid'] == cid for x in parsed):
                        parsed.append({
                            "colaborador": colab,
                            "setor": current_setor or "GERAL",
                            "inicio": inicio,
                            "termino": termino,
                            "duracao": duracao,
                            "cid": cid,
                            "descricao": descricao,
                            "ocorrencia": ocorrencia,
                            "dias": dias_num,
                            "data": inicio
                        })
    return parsed

def run_etl():
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        # 1. Buscar os arquivos
        file_atestados = find_file_in_drive(service, 'Atestados.CSV')
        file_afastados = find_file_in_drive(service, 'Afastados .CSV')
        file_acidentes = find_file_in_drive(service, 'Relatório de acidente.CSV')
        
        consolidated = {
            "atestados": [],
            "afastados": [],
            "acidentes": []
        }
        
        # Atestados
        if file_atestados:
            df_atestados = download_dataframe(service, file_atestados['id'], file_atestados['mimeType'], file_atestados['name'])
            raw_ate = json.loads(df_atestados.to_json(orient='records'))
            consolidated['atestados'] = parse_atestados(raw_ate)
            print(f"Arquivo origem: {file_atestados['name']} -> {len(consolidated['atestados'])} linhas processadas.")

        # Afastados
        if file_afastados:
            df_afastados = download_dataframe(service, file_afastados['id'], file_afastados['mimeType'], file_afastados['name'])
            raw_afa = json.loads(df_afastados.to_json(orient='records'))
            consolidated['afastados'] = parse_afastados(raw_afa)
            print(f"Arquivo origem: {file_afastados['name']} -> {len(consolidated['afastados'])} linhas processadas.")
            
        # Acidentes
        if file_acidentes:
            df_acidentes = download_dataframe(service, file_acidentes['id'], file_acidentes['mimeType'], file_acidentes['name'])
            raw_aci = json.loads(df_acidentes.to_json(orient='records'))
            consolidated['acidentes'] = parse_acidentes(raw_aci)
            print(f"Arquivo origem: {file_acidentes['name']} -> {len(consolidated['acidentes'])} linhas processadas.")
            
        # 2. Gerar payload JS final em memória
        js_str = "window.__SST_DATA__ = " + json.dumps(consolidated, ensure_ascii=False, indent=2) + ";"
        js_data = js_str.encode('utf-8')
        media = MediaIoBaseUpload(io.BytesIO(js_data), mimetype='application/javascript', resumable=True)
        
        # Salvar cópia local para uso via file://
        local_path = os.path.join(os.path.dirname(__file__), 'sst_data.js')
        with open(local_path, 'w', encoding='utf-8') as fp:
            fp.write(js_str)
        print(f"Arquivo local salvo com sucesso: {local_path}")

        # 3. Upload para o Drive (Destino) como sst_data.js
        q_exist = f"name='sst_data.js' and '{DEST_FOLDER}' in parents and trashed = false"
        exist_res = service.files().list(q=q_exist).execute().get('files', [])
        
        if exist_res:
            file_id = exist_res[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {
                'name': 'sst_data.js',
                'parents': [DEST_FOLDER]
            }
            service.files().create(body=file_metadata, media_body=media).execute()
            
        print("ETL concluído com sucesso. sst_data.js atualizado no Google Drive e localmente.")
        return True

    except Exception as e:
        print(f"Erro no ETL: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    run_etl()
