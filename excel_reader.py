import pandas as pd
import json
import re

def clean_value(val):
    if pd.isna(val) or val == ' ' or val == '\xa0':
        return None
    if isinstance(val, str):
        return val.strip()
    return val

def process_excel_files(extrato_path):
    # Lendo o arquivo HTML disfarçado de XLS
    df = pd.read_html(extrato_path, decimal=',', thousands='.', match='CADASTRO')[0]
    
    # Substituir nan e valores nulos
    df = df.where(pd.notnull(df), None)
    
    # Validação rigorosa de Schema
    colunas_obrigatorias = ['AUSENTE', 'LICENCA', 'QTD_SUSPENSOES', 'QTD_ADVERT_VERBAIS', 'QTD_ADVERT_ESCRITAS']
    colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
    if colunas_faltantes:
        raise ValueError(f"Mudança de Schema Detectada: As colunas obrigatórias {colunas_faltantes} não foram encontradas na planilha. O sistema de extração do RH pode ter sido alterado. Atualize o sistema ou a planilha para evitar dados falsos (falsos negativos).")
    
    
    # Determinar a origem baseada no path
    import os
    base_name = os.path.basename(extrato_path) if isinstance(extrato_path, str) else ""
    origem = base_name.replace("DP_-_Colaboradores_-_", "").replace(".xls", "").replace(".xlsx", "")
    if origem == "Listagem_detalhada_de_eventos_e_notificações":
        origem = "Listagem_detalhada"
        
    # Dicionário para armazenar o resultado agrupado pelo Cadastro
    colabs_dict = {}
    
    for idx, row in df.iterrows():
        cad = int(row['CADASTRO'])
        
        descricao_evento = str(row.get('DESCRICAO_EVENTO', '')).upper()
        afastado = str(row.get('AFASTADO', '')).strip().upper()

        # Helper para inteiros
        def safe_int(val):
            if val is None or pd.isna(val) or str(val).strip().upper() in ['', 'NAN', 'NONE']:
                return 0
            try:
                return int(float(str(val).replace(',', '.')))
            except:
                return 0

        if 'AUSENTE' in row:
            ausente_val = str(row.get('AUSENTE', '')).strip().upper() == 'SIM'
        else:
            ausente_val = 'FALTA' in descricao_evento

        if 'LICENCA' in row:
            licenca_val = str(row.get('LICENCA', '')).strip().upper() == 'SIM'
        else:
            licenca_val = afastado == 'SIM'

        if 'QTD_SUSPENSOES' in row:
            susp_val = safe_int(row.get('QTD_SUSPENSOES', 0))
        else:
            susp_raw = str(row.get('SUSPENSO', '')).strip().upper()
            if susp_raw == 'SIM':
                susp_val = 1
            else:
                susp_val = safe_int(susp_raw) if susp_raw not in ['NÃO', 'NAO', 'NON', 'NO', ''] else 0

        if 'QTD_ADVERT_VERBAIS' in row:
            advV_val = safe_int(row.get('QTD_ADVERT_VERBAIS', 0))
        else:
            advV_val = 1 if 'VERBAL' in descricao_evento else 0

        if 'QTD_ADVERT_ESCRITAS' in row:
            advE_val = safe_int(row.get('QTD_ADVERT_ESCRITAS', 0))
        else:
            advE_val = 1 if 'ESCRITA' in descricao_evento else 0

        # Garantir horas
        def get_float(val):
            try:
                if isinstance(val, str):
                    return float(val.replace('.', '').replace(',', '.'))
                return float(val) if val is not None else 0.0
            except:
                return 0.0

        if cad not in colabs_dict:
            # Processar o "setor" (Centro de Custo)
            centro_custo = clean_value(row.get('CENTRO_CUSTO'))
            setor = centro_custo
            if centro_custo and ' - ' in centro_custo:
                setor = centro_custo.split(' - ', 1)[1].strip()
            
            # Tratar Salario que pode vir como string ou float
            salario_raw = row.get('SALARIO', 0)
            try:
                if isinstance(salario_raw, str):
                    salario = float(salario_raw.replace('.', '').replace(',', '.'))
                else:
                    salario = float(salario_raw)
            except:
                salario = 0.0

            colab = {
                "cad": cad,
                "nome": clean_value(row.get('NOME')),
                "nasc": clean_value(row.get('DATA_NASCIMENTO')),
                "admissao": clean_value(row.get('DATA_ADMISSAO')),
                "deslig": clean_value(row.get('DATA_DESLIGAMENTO')),
                "cargo": clean_value(row.get('CARGO')),
                "salario": salario,
                "setor": setor,
                "local": clean_value(row.get('LOCAL')),
                "ausente": ausente_val,
                "licenca": licenca_val,
                "susp": susp_val,
                "advV": advV_val,
                "advE": advE_val,
                "evento": clean_value(row.get('DESCRICAO_EVENTO')),
                "cid": clean_value(row.get('DESCRICAO_CID_EVENTO')),
                "hFaltas": get_float(row.get('HORAS_FALTAS')) if 'HORAS_FALTAS' in row else 0.0,
                "hTrab": get_float(row.get('HORAS_TRABALHADAS')) if 'HORAS_TRABALHADAS' in row else 0.0,
                "hExtra": get_float(row.get('HORAS_EXTRAS')) if 'HORAS_EXTRAS' in row else 0.0,
                "origem": origem
            }
            colabs_dict[cad] = colab
        else:
            c = colabs_dict[cad]
            
            # Agregar eventos logicos
            if ausente_val:
                c['ausente'] = True
            if licenca_val:
                c['licenca'] = True
            
            c['susp'] += susp_val
            c['advV'] += advV_val
            c['advE'] += advE_val
            
            if 'HORAS_FALTAS' in row:
                c['hFaltas'] += get_float(row.get('HORAS_FALTAS'))
            if 'HORAS_TRABALHADAS' in row:
                c['hTrab'] += get_float(row.get('HORAS_TRABALHADAS'))
            if 'HORAS_EXTRAS' in row:
                c['hExtra'] += get_float(row.get('HORAS_EXTRAS'))
            
            # Se houver um evento novo e o antigo era nulo, pega o novo
            if clean_value(row.get('DESCRICAO_EVENTO')) and not c['evento']:
                c['evento'] = clean_value(row.get('DESCRICAO_EVENTO'))
            if clean_value(row.get('DESCRICAO_CID_EVENTO')) and not c['cid']:
                c['cid'] = clean_value(row.get('DESCRICAO_CID_EVENTO'))

    return list(colabs_dict.values())

if __name__ == '__main__':
    data = process_excel_files('DP_-_Colaboradores_-_Extrato_Diário.xls')
    print(f"Total colaboradores: {len(data)}")
    with open('colab_parsed.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Salvo em colab_parsed.json")
