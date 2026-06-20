import pandas as pd
import os

path = r"D:\Users\andre.WIN-UT7BSJO8U2I\Temp\DP_-_Colaboradores_-_Extrato_Diário.xls"
dfs = pd.read_html(path, decimal=',', thousands='.', match='CADASTRO')
df = dfs[0]

cols_to_check = ['AUSENTE', 'LICENCA', 'QTD_SUSPENSOES', 'QTD_ADVERT_VERBAIS', 'QTD_ADVERT_ESCRITAS']
for col in cols_to_check:
    if col in df.columns:
        print(f"{col} values:", df[col].unique().tolist()[:10])
    else:
        print(f"{col} not found!")

# Let's count them
if 'AUSENTE' in df.columns:
    print("Total Ausentes:", (df['AUSENTE'].str.strip().str.upper() == 'SIM').sum())
if 'LICENCA' in df.columns:
    print("Total Licenças:", (df['LICENCA'].str.strip().str.upper() == 'SIM').sum())
if 'QTD_ADVERT_VERBAIS' in df.columns:
    print("Total Adv Verbais:", df['QTD_ADVERT_VERBAIS'].fillna(0).astype(int).sum())
if 'QTD_ADVERT_ESCRITAS' in df.columns:
    print("Total Adv Escritas:", df['QTD_ADVERT_ESCRITAS'].fillna(0).astype(int).sum())
if 'QTD_SUSPENSOES' in df.columns:
    print("Total Suspensoes:", df['QTD_SUSPENSOES'].fillna(0).astype(int).sum())

