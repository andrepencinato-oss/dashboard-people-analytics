import pandas as pd

path = 'DP_-_Colaboradores_-_Listagem_detalhada_de_eventos_e_notificações.xls'
try:
    df = pd.read_html(path, decimal=',', thousands='.', match='CADASTRO')[0]
    
    # Drop rows without CADASTRO or NOME
    df = df.dropna(subset=['CADASTRO', 'NOME'])
    
    # Group by CADASTRO and get unique names
    collisions = {}
    for cad, group in df.groupby('CADASTRO'):
        unique_names = group['NOME'].unique()
        if len(unique_names) > 1:
            collisions[int(cad)] = unique_names.tolist()
            
    print(f"Total de registros na planilha: {len(df)}")
    print(f"Total de Cadastros unicos: {df['CADASTRO'].nunique()}")
    print(f"Total de Nomes unicos: {df['NOME'].nunique()}")
    
    if collisions:
        print(f"\\nENCONTRADOS {len(collisions)} CADASTROS COM COLISAO (nomes diferentes usando o mesmo cadastro):")
        for cad, names in collisions.items():
            print(f"- CADASTRO {cad}: {', '.join(names)}")
    else:
        print("\\nNENHUMA COLISAO ENCONTRADA. Cada Cadastro pertence a apenas uma pessoa.")

except Exception as e:
    print(f"Erro ao ler a planilha: {e}")
