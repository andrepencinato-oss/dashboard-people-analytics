import os
import pandas as pd
import excel_reader
import drive_sync

def run_diagnostics():
    print("Baixando arquivo mais recente...")
    try:
        file_path = drive_sync.fetch_latest_excel()
        print(f"Arquivo baixado para: {file_path}")
    except Exception as e:
        print(f"Erro no download: {e}")
        return

    print("\n--- COLUNAS BRUTAS EXTRAÍDAS DO EXCEL ---")
    try:
        df = pd.read_html(file_path, match='CADASTRO')[0]
        print(df.columns.tolist())
    except Exception as e:
        print(f"Falha na leitura bruta (read_html): {e}")

    print("\n--- VALIDAÇÃO DE TIPAGEM E VALORES (excel_reader.py) ---")
    try:
        dados = excel_reader.process_excel_files(file_path)
        if not dados:
            print("O parser retornou uma lista vazia.")
            return

        chaves_alvo = ['ausente', 'licenca', 'advV', 'advE', 'susp']
        
        print(f"Total de registros lidos: {len(dados)}")
        for chave in chaves_alvo:
            validos = [d for d in dados if d.get(chave) not in [False, 0, None, '', 'NaN', 'null']]
            print(f"Registros com '{chave}' preenchido/True: {len(validos)}")

        print("\n--- AMOSTRA DO PRIMEIRO REGISTRO ---")
        amostra = dados[0]
        print(f"Nome: {amostra.get('nome', 'N/A')}")
        for chave in chaves_alvo:
            valor = amostra.get(chave)
            print(f"{chave}: {valor} (Tipo: {type(valor).__name__})")

    except Exception as e:
        print(f"Falha ao executar o process_excel_files: {e}")

if __name__ == "__main__":
    run_diagnostics()
