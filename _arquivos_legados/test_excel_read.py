import pandas as pd
import codecs

try:
    with codecs.open('DP_-_Colaboradores_-_Extrato_Diário.xls', 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    df_list = pd.read_html(html)
    for i, df in enumerate(df_list):
        print(f"Table {i} shape: {df.shape}")
        if df.shape[0] >= 699:
            print(f"Table {i} row 699:\n", df.iloc[699])
except Exception as e:
    import traceback
    traceback.print_exc()
