import traceback

try:
    import excel_reader
except ImportError:
    import parser as excel_reader

try:
    print("--- INICIANDO DEBUG DE LEITURA ---")
    data = excel_reader.process_excel_files('DP_-_Colaboradores_-_Extrato_Diário.xls')
    print(f"Sucesso aparente na leitura. Número de registros: {len(data)}")
    if len(data) == 0:
        import pandas as pd
        print("Lendo dataframe cru para diagnóstico:")
        df = pd.read_html('DP_-_Colaboradores_-_Extrato_Diário.xls', decimal=',', thousands='.')
        print(f"Número de tabelas encontradas: {len(df)}")
        if len(df) > 0:
            print(f"Shape da tabela 0: {df[0].shape}")
            print(f"Colunas: {df[0].columns.tolist()}")
except Exception as e:
    print("--- ERRO FATAL CAPTURADO ---")
    print(traceback.format_exc())
