import os
import io
import re
import time
import itertools
import pandas as pd
import numpy as np
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = r'D:\Projeto geral\People analytics - GP'
TOKEN_PATH = os.path.join(BASE_DIR, 'core', 'token.json')
SCOPES = ['https://www.googleapis.com/auth/drive']
FILE_ID = '1o92c6a-k0KC4fSAVYiwzvp2vF1nXuZ1y'

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

def download_data():
    t0 = time.time()
    output_path_abs = os.path.join(os.path.dirname(__file__), 'downloaded_abs.xls')
    output_path_hc = os.path.join(os.path.dirname(__file__), 'downloaded_headcount.xlsx')
    output_path_afast = os.path.join(os.path.dirname(__file__), 'downloaded_afastamentos.xlsx')
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    sync_info = {"absenteismo": {"name": "", "date": ""}, "headcount": {"name": "", "date": ""}, "afastamentos": {"name": "", "date": ""}}
    
    print("[Absenteísmo] Buscando base no Drive (Dynamic Search)...")
    try:
        query_abs = "name contains 'Absenteismo 25' and trashed = false"
        results_abs = service.files().list(q=query_abs, fields='files(id, name, modifiedTime, mimeType)', orderBy='modifiedTime desc', pageSize=1).execute()
        files_abs = results_abs.get('files', [])
        if files_abs:
            abs_id = files_abs[0]['id']
            abs_mime = files_abs[0].get('mimeType', '')
            sync_info["absenteismo"]["name"] = files_abs[0]['name']
            sync_info["absenteismo"]["date"] = files_abs[0].get('modifiedTime')
            print(f"[API Abs] Encontrado: {files_abs[0]['name']} | ID: {abs_id}")
            
            if os.path.exists(output_path_abs):
                print(f"[CACHE] Apagando arquivo local antigo de Absenteísmo antes de baixar...")
                os.remove(output_path_abs)
                
            if abs_mime == 'application/vnd.google-apps.spreadsheet':
                request = service.files().export_media(fileId=abs_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                request = service.files().get_media(fileId=abs_id)
            fh = io.FileIO(output_path_abs, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.close()
        else:
            print("[Absenteísmo] ERRO CRÍTICO: Nenhum arquivo encontrado!")
    except Exception as e:
        print(f"[Absenteísmo] Erro dinâmico: {e}")
    
    print("[Headcount] Buscando base de Headcount no Drive (Dynamic Search)...")
    if os.path.exists(output_path_hc):
        print(f"[CACHE] Apagando arquivo local antigo de Headcount antes de baixar...")
        os.remove(output_path_hc)

    try:
        query_hc = "name contains 'Headcount' and trashed = false"
        results_hc = service.files().list(q=query_hc, fields='files(id, name, modifiedTime, mimeType)', orderBy='modifiedTime desc', pageSize=1).execute()
        files_hc = results_hc.get('files', [])
        if files_hc:
            hc_id = files_hc[0]['id']
            hc_mime = files_hc[0].get('mimeType', '')
            sync_info["headcount"]["name"] = files_hc[0]['name']
            sync_info["headcount"]["date"] = files_hc[0].get('modifiedTime')
            print(f"[API HC] Encontrado: {files_hc[0]['name']} | ID: {hc_id}")
            print(f"[Headcount] Baixando do Drive...")
            if hc_mime == 'application/vnd.google-apps.spreadsheet':
                request_hc = service.files().export_media(fileId=hc_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                request_hc = service.files().get_media(fileId=hc_id)
            fh_hc = io.FileIO(output_path_hc, mode='wb')
            dl_hc = MediaIoBaseDownload(fh_hc, request_hc)
            done_hc = False
            while not done_hc:
                _, done_hc = dl_hc.next_chunk()
            fh_hc.close()
            mod_time_local = time.ctime(os.path.getmtime(output_path_hc))
            print(f"[CACHE] Novo arquivo local criado com sucesso. Modificado em: {mod_time_local}")
        else:
            print("[Headcount] ERRO CRÍTICO: Nenhum arquivo encontrado!")
    except Exception as e:
        print(f"[Headcount] Erro dinâmico ao baixar: {e}")
        
    print("[Afastamentos] Buscando base no Drive...")
    if os.path.exists(output_path_afast):
        print(f"[CACHE] Apagando arquivo local antigo de Afastamentos antes de baixar...")
        os.remove(output_path_afast)

    try:
        query_afast = "'1-tDGV3W5xK3WvCQddu8P3qjcnuen8HV4' in parents and trashed = false"
        results_afast = service.files().list(q=query_afast, fields='files(id, name, modifiedTime, mimeType)', orderBy='modifiedTime desc', pageSize=1).execute()
        files_afast = results_afast.get('files', [])
        if files_afast:
            afast_id = files_afast[0]['id']
            afast_mime = files_afast[0].get('mimeType', '')
            sync_info["afastamentos"]["name"] = files_afast[0]['name']
            sync_info["afastamentos"]["date"] = files_afast[0].get('modifiedTime')
            print(f"[API Afastamentos] Encontrado: {files_afast[0]['name']} | ID: {afast_id}")
            if afast_mime == 'application/vnd.google-apps.spreadsheet':
                request_afast = service.files().export_media(fileId=afast_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                request_afast = service.files().get_media(fileId=afast_id)
            fh_afast = io.FileIO(output_path_afast, mode='wb')
            dl_afast = MediaIoBaseDownload(fh_afast, request_afast)
            done_afast = False
            while not done_afast:
                _, done_afast = dl_afast.next_chunk()
            fh_afast.close()
        else:
            print("[Afastamentos] ERRO: Nenhum arquivo encontrado na pasta especificada.")
    except Exception as e:
        print(f"[Afastamentos] Erro dinâmico ao baixar: {e}")

    try:
        import json
        with open(os.path.join(os.path.dirname(__file__), 'sync_info.json'), 'w', encoding='utf-8') as f:
            json.dump(sync_info, f, ensure_ascii=False)
    except Exception as e:
        print(f"[SYNC] Erro ao salvar sync_info.json: {e}")
    
    t1 = time.time()
    print(f"[PERF] Download Drive concluído em {t1-t0:.3f} segundos.")
    return output_path_abs, output_path_hc, output_path_afast

def parse_hours_to_decimal(time_str):
    match = re.search(r"(\d{2,3}):(\d{2})", str(time_str))
    if match:
        h = int(match.group(1))
        m = int(match.group(2))
        return round(h + (m / 60.0), 2)
    return 0.0

def get_slot_name(index, total_slots):
    if total_slots == 2: return ['Entrada', 'Saída'][index]
    if total_slots == 4: return ['Entrada', 'Saída Almoço', 'Retorno Almoço', 'Saída'][index]
    if index == 0: return 'Entrada'
    if index == total_slots - 1: return 'Saída'
    return f'Marcação {index + 1}'

def parse_time_to_minutes(t_str):
    try:
        h, m = map(int, t_str.split(':'))
        return h * 60 + m
    except:
        return 0

def format_diff(diff_mins):
    diff_abs = abs(diff_mins)
    h_diff = diff_abs // 60
    m_diff = diff_abs % 60
    return f"{h_diff}h {m_diff:02d}m" if h_diff > 0 else f"{m_diff}m"

def format_name(full_name):
    if not full_name: return ""
    parts = str(full_name).strip().title().split()
    if len(parts) > 1:
        return f"{parts[0]} {parts[-1]}"
    return parts[0] if parts else ""

def generate_evidence(expected_str, actual_str, penalty_str):
    expected = expected_str.split()
    actual = actual_str.split()
    if not expected: return 'Sem escala na base'
    if not actual: 
        j = ' '.join(expected)
        return f'Faltou Tudo (Prev: {j})'
    if len(actual) > len(expected): 
        return f'Marcações extras: {" ".join(actual)}'
    
    penalty_mins = parse_time_to_minutes(penalty_str)
    if penalty_mins == 0: return 'OK (no horário)'
    
    exp_mins = [parse_time_to_minutes(t) for t in expected]
    act_mins = [parse_time_to_minutes(t) for t in actual]
    best_assignment, min_cost = None, float('inf')
    
    for comb in itertools.combinations(range(len(expected)), len(actual)):
        cost = sum(abs(act_mins[i] - exp_mins[comb[i]]) for i in range(len(actual)))
        if cost < min_cost:
            min_cost = cost
            best_assignment = comb
            
    infractions = []
    for i in range(len(expected)):
        slot_name = get_slot_name(i, len(expected))
        if i not in best_assignment:
            infractions.append({'msg': f'Faltou {slot_name} ({expected[i]})', 'mins': penalty_mins})
        else:
            act_idx = best_assignment.index(i)
            diff_mins = act_mins[act_idx] - exp_mins[i]
            
            is_arrival = (i % 2 == 0)
            is_departure = (i % 2 == 1)
            
            if is_arrival and diff_mins > 5:
                infractions.append({'msg': f'Atraso {slot_name} ({format_diff(diff_mins)}): Bateu {actual[act_idx]}, Previsto {expected[i]}', 'mins': diff_mins})
            elif is_departure and diff_mins < -5:
                infractions.append({'msg': f'Saída Antecipada {slot_name} ({format_diff(diff_mins)}): Bateu {actual[act_idx]}, Previsto {expected[i]}', 'mins': abs(diff_mins)})
                
    best_subset = infractions
    best_diff = float('inf')
    
    for r in range(1, len(infractions) + 1):
        for subset in itertools.combinations(infractions, r):
            total_subset_mins = sum(item['mins'] for item in subset)
            diff = abs(total_subset_mins - penalty_mins)
            if diff < best_diff:
                best_diff = diff
                best_subset = subset
                
    if best_diff <= 15:
        return ' | '.join(item['msg'] for item in best_subset)
    
    return ' | '.join(item['msg'] for item in infractions) if infractions else 'OK (no horário)'

def process_absenteismo(file_path):
    t0 = time.time()
    print("[Absenteísmo] Processando planilha no Pandas...")
    try:
        import openpyxl.descriptors.base
        orig_set = openpyxl.descriptors.base.Typed.__set__
        def patched_set(self, instance, value):
            try: orig_set(self, instance, value)
            except TypeError: pass
        openpyxl.descriptors.base.Typed.__set__ = patched_set
        
        import openpyxl.styles.named_styles
        orig_init = openpyxl.styles.named_styles._NamedCellStyle.__init__
        def patched_init(self, *args, **kwargs):
            if 'builtInId' in kwargs:
                kwargs['builtinId'] = kwargs.pop('builtInId')
            orig_init(self, *args, **kwargs)
        openpyxl.styles.named_styles._NamedCellStyle.__init__ = patched_init
    except Exception:
        pass

    try:
        df = pd.read_excel(file_path, engine='openpyxl')
    except Exception:
        df = pd.read_excel(file_path, engine='xlrd')
    df = df.fillna('')

    current_cod = ""
    current_nome = ""
    current_schedule = ""
    
    records = []
    inconsistent_lines = 0

    for index, row in df.iterrows():
        val0 = row.iloc[0]
        val1 = row.iloc[1] if len(row) > 1 else ""
        val2 = row.iloc[2] if len(row) > 2 else ""
        
        col0 = str(val0).strip() if pd.notna(val0) else ""
        col1 = str(val1).strip() if pd.notna(val1) else ""
        col2 = str(val2).strip() if pd.notna(val2) else ""

        # Escala (movido para antes do 'continue' de linha vazia pois a linha da escala tem as primeiras colunas em branco)
        row_strs = [str(x).strip() for x in row if pd.notna(x) and str(x).strip() != ""]
        if any(':' in x for x in row_strs) and not any(isinstance(x, datetime) for x in row):
            achou_escala = False
            for x in row_strs:
                if ':' in x and len(x) > 10 and not any(c.isalpha() for c in x):
                    current_schedule = x
                    achou_escala = True
                    break
            if achou_escala:
                continue

        if not col0 and not col1:
            continue

        # Matrícula e Nome
        if pd.isna(val0) and col1.isdigit() and col2 != "":
            current_cod = col1
            current_nome = format_name(col2)
            continue
            
        if col0.isdigit() and col1 != "" and col2 == "" and "Total" not in col0:
            current_cod = col0
            current_nome = format_name(col1)
            continue
            

        # Data
        is_date = False
        data_str = ""
        dt = None
        if isinstance(val0, datetime):
            is_date = True
            dt = val0
            data_str = dt.strftime("%d/%m/%y")
        elif col0 and len(col0) == 8 and col0.count('/') == 2:
            is_date = True
            data_str = col0
            try:
                dt = datetime.strptime(data_str, "%d/%m/%y")
            except:
                is_date = False

        if is_date:
            # Pular colunas vazias para achar os dados consistentes
            # [Data, Dia, Marcacoes, SitCod, SitDesc, Horas]
            # Ocasionalmente, Marcacoes não existe.
            cols = [x for x in row if pd.notna(x) and str(x).strip() != ""]
            if len(cols) < 4:
                continue
                
            dia_semana = str(cols[1]).strip().lower()
            
            # Tentar achar a situação (SitCod costuma ser número ou código)
            # A hora (última coluna) pode ser datetime.time ou string
            horas_raw = cols[-1]
            if hasattr(horas_raw, 'strftime'):
                horas_str = horas_raw.strftime("%H:%M")
            else:
                horas_str = str(horas_raw).strip()
                if "00:00:00" in horas_str: horas_str = "00:00" # Limpeza
                
            sit_desc = str(cols[-2]).strip()
            sit_cod = str(cols[-3]).strip()
            
            # E as marcações? Se sobrar algo entre Dia e SitCod, são as marcações.
            marcacoes_raw = ""
            if len(cols) >= 6:
                marcacoes_raw = str(cols[2]).strip()
            
            marcacoes_formatada = generate_evidence(current_schedule, marcacoes_raw, horas_str)
            
            if current_cod == "":
                inconsistent_lines += 1
                continue
            
            if not sit_cod and not horas_str:
                continue
                
            horas_dec = parse_hours_to_decimal(horas_str)
            if horas_dec == 0.0 and sit_cod != '999': 
                continue
            
            if sit_cod == "" and horas_dec > 0:
                inconsistent_lines += 1
                sit_desc = "Sem Justificativa"
                
            is_seg_sex = 'seg' in dia_semana or 'sex' in dia_semana
            is_inconsistent = sit_cod == "" or sit_desc == "Sem Justificativa"
            
            alertas = []
            if is_seg_sex:
                alertas.append("Emenda (Seg/Sex)")
            if is_inconsistent:
                alertas.append("Inconsistência/Sem Justificativa")
                
            try:
                if not dt:
                    dt = datetime.strptime(data_str, "%d/%m/%y")
                month_year = dt.strftime("%Y-%m")
                full_date = dt.strftime("%Y-%m-%d")
                year = dt.strftime("%Y")
            except:
                month_year = "Desconhecido"
                full_date = "Desconhecido"
                year = "Desconhecido"

            records.append({
                'cod': current_cod,
                'nome': current_nome,
                'data': data_str,
                'data_iso': full_date,
                'dia': dia_semana.capitalize(),
                'mes_ano': month_year,
                'ano': year,
                'sit_cod': sit_cod if sit_cod else "N/A",
                'sit_desc': sit_desc,
                'horas_str': horas_str,
                'horas_dec': horas_dec,
                'alertas': ", ".join(alertas),
                'marcacoes': marcacoes_formatada,
                'escala': current_schedule,
                'marcacoes_raw': marcacoes_raw
            })

    t1 = time.time()
    print(f"[Absenteísmo] {len(records)} registros apurados encontrados. Inconsistências: {inconsistent_lines}")
    print(f"[PERF] Processamento do Pandas e Parse concluído em {t1-t0:.3f} segundos.")
    return records, inconsistent_lines

def get_dashboard_data():
    t_start = time.time()
    file_path_abs, file_path_hc, file_path_afast = download_data()
    records, inconsistent_lines = process_absenteismo(file_path_abs)
    
    t0_agregacao = time.time()
    df = pd.DataFrame(records)
    
    if df.empty:
        return {"error": "Sem dados"}

    # --- MERGE HEADCOUNT ---
    print("[Headcount] Realizando Merge com a base de Absenteísmo...")
    try:
        if os.path.exists(file_path_hc):
            # Leitura Bruta: Ignora cabeçalhos e pula as primeiras linhas de sujeira
            df_hc = pd.read_excel(file_path_hc, engine='openpyxl', header=None, skiprows=4)
            
            # Isolamento (iloc): Pega a coluna 0 (Matrícula) e 8 (Área - Coluna I)
            df_hc = df_hc.iloc[:, [0, 8]]
            df_hc.columns = ['Cad_HC', 'Area_HC']
            
            # Formatação Premium da Área (Deep Clean, Trim, Title)
            df_hc['Area_HC'] = df_hc['Area_HC'].astype(str).str.split('-').str[-1].str.replace(r'\s+', ' ', regex=True).str.replace(r'\s*-\s*', ' - ', regex=True).str.strip().str.title()
            df_hc['Area_HC'] = df_hc['Area_HC'].replace({'Nan': 'Sem Área', 'None': 'Sem Área'})
            
            # Tratamento numérico para remover zeros à esquerda
            df['cod_str'] = pd.to_numeric(df['cod'], errors='coerce').astype('Int64').astype(str)
            df_hc['Cad_HC'] = pd.to_numeric(df_hc['Cad_HC'], errors='coerce').astype('Int64').astype(str)
            
            print("[Merge Debug] Abs keys:", df['cod_str'].dropna().unique()[:5].tolist())
            print("[Merge Debug] HC keys:", df_hc['Cad_HC'].dropna().unique()[:5].tolist())
            
            # --- MERGE AFASTAMENTOS E REGRAS DE DENOMINADOR ---
            print("[Afastamentos] Realizando processamento e Join...")
            if os.path.exists(file_path_afast):
                df_afast_full = pd.read_excel(file_path_afast, engine='openpyxl')
                # Preencher matrículas vazias para baixo (mesclar células do Excel)
                if not df_afast_full.empty:
                    df_afast_full.iloc[:, 0] = df_afast_full.iloc[:, 0].ffill()
                
                # Colunas: 0 (Cadastro), 10 (Afastamento Início), 14 (Situação/Motivo), 16 (Término)
                df_afast_clean = df_afast_full.iloc[:, [0, 10, 14, 16]].copy()
                df_afast_clean.columns = ['Cad_Afast', 'inicio', 'motivo_afastamento', 'retorno_afastamento']
                df_afast_clean['Cad_Afast'] = pd.to_numeric(df_afast_clean['Cad_Afast'], errors='coerce').astype('Int64').astype(str)
                df_afast_clean['inicio'] = pd.to_datetime(df_afast_clean['inicio'], errors='coerce')
                df_afast_clean['retorno_dt'] = pd.to_datetime(df_afast_clean['retorno_afastamento'], errors='coerce')
                df_afast_clean = df_afast_clean.dropna(subset=['Cad_Afast', 'inicio'])
                
                # --- HEADCOUNT ATUAL ---
                # Considera afastado "hoje" quem tem inicio <= hoje e (retorno vazio ou >= hoje)
                hoje = pd.Timestamp.today()
                df_afast_atual = df_afast_clean[
                    (df_afast_clean['inicio'] <= hoje) &
                    (df_afast_clean['retorno_dt'].isna() | (df_afast_clean['retorno_dt'] >= hoje))
                ].copy()
                df_afast_atual = df_afast_atual.drop_duplicates(subset=['Cad_Afast'])
                
                df_hc = pd.merge(df_hc, df_afast_atual[['Cad_Afast']], left_on='Cad_HC', right_on='Cad_Afast', how='left')
                df_hc['Status_HC'] = np.where(df_hc['Cad_Afast'].notna(), 'Afastado', 'Ativo')
                df_hc.drop(columns=['Cad_Afast'], inplace=True)
            else:
                print("[Afastamentos] Arquivo não encontrado.")
                df_hc['Status_HC'] = 'Ativo'
                df_afast_clean = pd.DataFrame(columns=['Cad_Afast', 'inicio', 'motivo_afastamento', 'retorno_afastamento', 'retorno_dt'])
                
            headcount_total = df_hc['Cad_HC'].nunique()
            headcount_ativo = df_hc[df_hc['Status_HC'] == 'Ativo']['Cad_HC'].nunique()
            total_afastados = headcount_total - headcount_ativo
            print(f"[Afastamentos] HCA {headcount_ativo} | HC {headcount_total} | Afast {total_afastados}")
            
            # --- CRUZAMENTO COM ABSENTEÍSMO (Múltiplos Afastamentos por pessoa) ---
            # 1. Trazer área do Headcount
            df = pd.merge(df, df_hc[['Cad_HC', 'Area_HC']], left_on='cod_str', right_on='Cad_HC', how='inner')
            df.rename(columns={'Area_HC': 'area'}, inplace=True)
            df['area'] = df['area'].fillna('Sem Área')
            df.drop(columns=['Cad_HC'], inplace=True)
            
            # 2. Avaliar se cada evento caiu dentro de um período de afastamento
            df['data_evento_dt'] = pd.to_datetime(df['data_iso'], errors='coerce')
            df = df.reset_index(drop=True)
            df['index_orig'] = df.index # Guardar ordem original
            
            if not df_afast_clean.empty:
                df_merged = pd.merge(df, df_afast_clean, left_on='cod_str', right_on='Cad_Afast', how='left')
                
                mask_afastado = (
                    df_merged['inicio'].notna() &
                    (df_merged['data_evento_dt'] >= df_merged['inicio']) &
                    (df_merged['retorno_dt'].isna() | (df_merged['data_evento_dt'] <= df_merged['retorno_dt']))
                )
                
                df_merged['is_valid_afast'] = mask_afastado
                # Limpar os dados de afastamento das linhas que não deram match
                df_merged.loc[~mask_afastado, ['inicio', 'motivo_afastamento', 'retorno_afastamento', 'retorno_dt']] = np.nan
                
                # Para eventos com múltiplos joins, manter o que tem afastamento válido (se houver)
                df_merged = df_merged.sort_values(by=['index_orig', 'is_valid_afast'], ascending=[True, False])
                df_final = df_merged.drop_duplicates(subset=['index_orig']).copy()
                
                df_final['Status'] = np.where(df_final['is_valid_afast'] == True, 'Afastado', 'Ativo')
                df_final['motivo_afastamento'] = df_final['motivo_afastamento'].fillna('')
                df_final['retorno_afastamento'] = df_final['retorno_dt'].dt.strftime('%d/%m/%Y').fillna('')
                
                df_final.drop(columns=['index_orig', 'data_evento_dt', 'Cad_Afast', 'inicio', 'retorno_dt', 'is_valid_afast'], inplace=True)
                df = df_final
            else:
                df['Status'] = 'Ativo'
                df['motivo_afastamento'] = ''
                df['retorno_afastamento'] = ''
                df.drop(columns=['index_orig', 'data_evento_dt'], inplace=True)
                
            df.drop(columns=['cod_str'], inplace=True)
        else:
            print("[Headcount] Arquivo não encontrado.")
            df['area'] = 'Sem Área'
            df['Status'] = 'Ativo'
            df['motivo_afastamento'] = ''
            df['retorno_afastamento'] = ''
            headcount_ativo = 0
            headcount_total = 0
            total_afastados = 0
    except Exception as e:
        print(f"[Headcount] Erro no merge: {e}")
        df['area'] = 'Sem Área'
        df['Status'] = 'Ativo'
        df['motivo_afastamento'] = ''
        df['retorno_afastamento'] = ''
        headcount_ativo = 0
        headcount_total = 0
        total_afastados = 0
    # -----------------------
        
    df_horas = df[df['horas_dec'] > 0].copy()
    
    # REGRA DE NEGÓCIO: Faltas do dia inteiro (>= 8.5 horas)
    df_horas.loc[(df_horas['sit_cod'] == '015') & (df_horas['horas_dec'] >= 8.5), 'sit_desc'] = 'Faltas integrais'
    
    # Converter para datetime no dataframe principal para que .dt funcione na auditoria
    df_horas['mes_ano'] = pd.to_datetime(df_horas['mes_ano'], errors='coerce')
    
    # 4. Cálculo Isolado: Filtrar a base na memória apenas para a matemática do Absenteísmo
    df_math = df_horas[df_horas['Status'] == 'Ativo'].copy()
    
    total_horas = df_math['horas_dec'].sum()
    total_eventos = len(df_math)
    colaboradores_unicos = df_math['cod'].nunique()
    freq_index = total_eventos / colaboradores_unicos if colaboradores_unicos > 0 else 0

    if not df_math.empty:
        max_month_date = df_math['mes_ano'].max()
    else:
        max_month_date = pd.Timestamp.today()
    
    current_month_str = max_month_date.strftime("%Y-%m")
    prev_month_date = max_month_date - pd.DateOffset(months=1)
    prev_month_str = prev_month_date.strftime("%Y-%m")
    
    current_month_hours = df_math[df_math['mes_ano'].dt.strftime("%Y-%m") == current_month_str]['horas_dec'].sum() if not df_math.empty else 0
    prev_month_hours = df_math[df_math['mes_ano'].dt.strftime("%Y-%m") == prev_month_str]['horas_dec'].sum() if not df_math.empty else 0
    
    if prev_month_hours > 0:
        mom_var = ((current_month_hours - prev_month_hours) / prev_month_hours) * 100
    else:
        mom_var = 0.0

    if not df_math.empty:
        seg_sex_events = df_math[df_math['dia'].isin(['Seg', 'Sex'])]
        seg_sex_hours = seg_sex_events['horas_dec'].sum()
    else:
        seg_sex_hours = 0
    seg_sex_perc = (seg_sex_hours / total_horas * 100) if total_horas > 0 else 0

    top_colab = df_math.groupby(['cod', 'nome'])['horas_dec'].sum().reset_index()
    top_colab = top_colab.sort_values(by='horas_dec', ascending=False).head(10)
    
    situacoes = df_math.groupby(['sit_cod', 'sit_desc'])['horas_dec'].sum().reset_index()
    situacoes['label'] = situacoes['sit_cod'] + ' - ' + situacoes['sit_desc']
    situacoes = situacoes.sort_values(by='horas_dec', ascending=False)
    
    top_sit = situacoes.iloc[0]['label'] if len(situacoes) > 0 else "Nenhuma"
    
    evolucao_mes = df_math.groupby(df_math['mes_ano'].dt.strftime("%Y-%m"))['horas_dec'].sum().reset_index() if not df_math.empty else pd.DataFrame(columns=['mes_ano', 'horas_dec'])
    evolucao_mes.rename(columns={'mes_ano': 'label', 'horas_dec': 'value'}, inplace=True)
    
    evolucao_ano = df_math.groupby('ano')['horas_dec'].sum().reset_index() if not df_math.empty else pd.DataFrame(columns=['ano', 'horas_dec'])
    evolucao_ano.rename(columns={'ano': 'label', 'horas_dec': 'value'}, inplace=True)
    
    evolucao_dia = df_math.groupby('data_iso')['horas_dec'].sum().reset_index() if not df_math.empty else pd.DataFrame(columns=['data_iso', 'horas_dec'])
    evolucao_dia = evolucao_dia.sort_values(by='data_iso').tail(30)
    evolucao_dia.rename(columns={'data_iso': 'label', 'horas_dec': 'value'}, inplace=True)

    yoy_current_year = df_math[df_math['mes_ano'].dt.strftime("%Y-%m") == current_month_str]['horas_dec'].sum() if not df_math.empty else 0
    yoy_prev_year_date = max_month_date - pd.DateOffset(years=1)
    yoy_prev_year_str = yoy_prev_year_date.strftime("%Y-%m")
    yoy_prev_year = df_math[df_math['mes_ano'].dt.strftime("%Y-%m") == yoy_prev_year_str]['horas_dec'].sum() if not df_math.empty else 0
    
    # --- CÁLCULO DOS DIAS ÚTEIS E HORAS PREVISTAS (QA TRAVAS) ---
    dias_uteis = 0
    if not df_math.empty:
        try:
            min_date = df_math['mes_ano'].min()
            max_date = df_math['mes_ano'].max()
            dias_uteis = int(np.busday_count(min_date.date(), (max_date + pd.Timedelta(days=1)).date()))
        except Exception as e:
            print(f"[QA] Erro ao calcular busday_count: {e}")
            dias_uteis = 0

    if dias_uteis <= 0 or headcount_ativo <= 0:
        horas_previstas = 0
    else:
        horas_previstas = headcount_ativo * dias_uteis * 8.8

    if horas_previstas == 0:
        taxa_absenteismo = 0.0
    else:
        taxa_absenteismo = (total_horas / horas_previstas) * 100
    # -----------------------------------------------------------
    
    t1_agregacao = time.time()
    print(f"[PERF] Agregações e Agrupamentos concluídos em {t1_agregacao-t0_agregacao:.3f} segundos.")
    
    t_end = time.time()
    print(f"[PERF] get_dashboard_data TOTAL executado em {t_end-t_start:.3f} segundos.")
    
    sync_info = {}
    try:
        import json
        with open(os.path.join(os.path.dirname(__file__), 'sync_info.json'), 'r', encoding='utf-8') as f:
            sync_info = json.load(f)
    except Exception as e:
        print(f"[SYNC] Erro lendo sync_info: {e}")

    return {
        "sync_info": sync_info,
        "kpis": {
            "total_horas": round(total_horas, 2),
            "mom_var": round(mom_var, 2),
            "current_month_str": current_month_str,
            "situacao_critica": top_sit,
            "freq_index": round(freq_index, 2),
            "seg_sex_perc": round(seg_sex_perc, 2),
            "inconsistent_lines": inconsistent_lines,
            "taxa_absenteismo": round(taxa_absenteismo, 2),
            "horas_previstas": round(horas_previstas, 2),
            "headcount_ativo": headcount_ativo,
            "headcount_total": headcount_total,
            "total_afastados": total_afastados,
            "dias_uteis": dias_uteis
        },
        "top_colaboradores": top_colab[['nome', 'horas_dec']].to_dict(orient='records'),
        "situacoes": situacoes[['label', 'horas_dec']].to_dict(orient='records'),
        "evolucao": {
            "mes": evolucao_mes.to_dict(orient='records'),
            "ano": evolucao_ano.to_dict(orient='records'),
            "dia": evolucao_dia.to_dict(orient='records')
        },
        "yoy": {
            "current_month_label": current_month_str,
            "current_month_val": round(yoy_current_year, 2),
            "prev_year_label": yoy_prev_year_str,
            "prev_year_val": round(yoy_prev_year, 2)
        },
        "auditoria": (
            df_horas.assign(mes_ano=df_horas['mes_ano'].dt.strftime('%Y-%m'))
            [['cod', 'nome', 'area', 'data', 'data_iso', 'mes_ano', 'dia', 'sit_cod', 'sit_desc', 'horas_str', 'horas_dec', 'alertas', 'marcacoes', 'escala', 'marcacoes_raw', 'Status', 'motivo_afastamento', 'retorno_afastamento']]
        ).to_dict(orient='records')
    }
