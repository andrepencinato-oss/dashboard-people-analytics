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
    
    # Dicionário para armazenar o resultado agrupado pelo Cadastro
    colabs_dict = {}
    
    for idx, row in df.iterrows():
        cad = int(row['CADASTRO'])
        
        # Helper interno para tratar SUSPENSO
        susp_raw = str(row.get('SUSPENSO', '')).strip().upper()
        susp_val = 0
        if susp_raw == 'SIM':
            susp_val = 1
        elif susp_raw in ['NÃO', 'NAO', 'NON', 'NO', '', 'NONE', 'NAN']:
            susp_val = 0
        else:
            try:
                susp_val = int(float(susp_raw.replace(',', '.')))
            except ValueError:
                print(f"AVISO: Valor inválido na coluna SUSPENSO para o cadastro {cad}: '{susp_raw}'")
                susp_val = 0

        descricao_evento = str(row.get('DESCRICAO_EVENTO', '')).upper()
        afastado = str(row.get('AFASTADO', '')).strip().upper()
        
        ausente_val = 'FALTA' in descricao_evento
        licenca_val = afastado == 'SIM'
        advV_val = 1 if 'VERBAL' in descricao_evento else 0
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
                "hExtra": get_float(row.get('HORAS_EXTRAS')) if 'HORAS_EXTRAS' in row else 0.0
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
