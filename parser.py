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
    df = pd.read_html(extrato_path, decimal=',', thousands='.')[0]
    
    # Substituir nan e valores nulos
    df = df.where(pd.notnull(df), None)
    
    # Dicionário para armazenar o resultado agrupado pelo Cadastro
    colabs_dict = {}
    
    for idx, row in df.iterrows():
        cad = int(row['CADASTRO'])
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

            # Garantir booleanos
            ausente = str(row.get('AUSENTE', '')).strip().lower() == 'sim'
            licenca = str(row.get('LICENCA', '')).strip().lower() == 'sim'
            
            # Garantir horas
            def get_float(val):
                try:
                    if isinstance(val, str):
                        return float(val.replace('.', '').replace(',', '.'))
                    return float(val) if val is not None else 0.0
                except:
                    return 0.0

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
                "ausente": ausente,
                "licenca": licenca,
                "susp": int(get_float(row.get('QTD_SUSPENSOES'))),
                "advV": int(get_float(row.get('QTD_ADVERT_VERBAIS'))),
                "advE": int(get_float(row.get('QTD_ADVERT_ESCRITAS'))),
                "evento": clean_value(row.get('DESCRICAO_EVENTO')),
                "cid": clean_value(row.get('DESCRICAO_CID_EVENTO')),
                "hFaltas": get_float(row.get('HORAS_FALTAS')),
                "hTrab": get_float(row.get('HORAS_TRABALHADAS')),
                "hExtra": get_float(row.get('HORAS_EXTRAS'))
            }
            colabs_dict[cad] = colab
        else:
            # Se a pessoa aparecer de novo, precisamos agregar as horas, eventos e advertências
            c = colabs_dict[cad]
            def get_float(val):
                try:
                    if isinstance(val, str):
                        return float(val.replace('.', '').replace(',', '.'))
                    return float(val) if val is not None else 0.0
                except:
                    return 0.0

            c['susp'] = max(c['susp'], int(get_float(row.get('QTD_SUSPENSOES'))))
            c['advV'] = max(c['advV'], int(get_float(row.get('QTD_ADVERT_VERBAIS'))))
            c['advE'] = max(c['advE'], int(get_float(row.get('QTD_ADVERT_ESCRITAS'))))
            
            c['hFaltas'] += get_float(row.get('HORAS_FALTAS'))
            c['hTrab'] += get_float(row.get('HORAS_TRABALHADAS'))
            c['hExtra'] += get_float(row.get('HORAS_EXTRAS'))
            
            # Se houver um evento novo e o antigo era nulo, pega o novo
            if clean_value(row.get('DESCRICAO_EVENTO')) and not c['evento']:
                c['evento'] = clean_value(row.get('DESCRICAO_EVENTO'))
            if clean_value(row.get('DESCRICAO_CID_EVENTO')) and not c['cid']:
                c['cid'] = clean_value(row.get('DESCRICAO_CID_EVENTO'))

            if str(row.get('AUSENTE', '')).strip().lower() == 'sim':
                c['ausente'] = True
            if str(row.get('LICENCA', '')).strip().lower() == 'sim':
                c['licenca'] = True

    return list(colabs_dict.values())

if __name__ == '__main__':
    data = process_excel_files('DP_-_Colaboradores_-_Extrato_Diário.xls')
    print(f"Total colaboradores: {len(data)}")
    with open('colab_parsed.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Salvo em colab_parsed.json")
