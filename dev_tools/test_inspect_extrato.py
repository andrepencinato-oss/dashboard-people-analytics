import pandas as pd
import glob
import os

path = r"D:\Users\andre.WIN-UT7BSJO8U2I\Temp\DP_-_Colaboradores_-_Extrato_Diário.xls"

dfs = pd.read_html(path, decimal=',', thousands='.', match='CADASTRO')
df = dfs[0]

print("Columns:", df.columns.tolist())
if 'AFASTADO' in df.columns:
    print("AFASTADO values:", df['AFASTADO'].unique().tolist())
if 'SUSPENSO' in df.columns:
    print("SUSPENSO values:", df['SUSPENSO'].unique().tolist())
if 'DESCRICAO_EVENTO' in df.columns:
    print("DESCRICAO_EVENTO values:")
    print(df['DESCRICAO_EVENTO'].value_counts().head(20))
