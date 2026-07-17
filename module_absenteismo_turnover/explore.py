import pandas as pd
import sys

file_path = r"D:\Projeto geral\People analytics - GP\module_absenteismo_turnover\Absenteismo 25_26.XLS"
try:
    df = pd.read_excel(file_path, engine='xlrd')
    print("Read with xlrd")
except Exception as e:
    try:
        df_list = pd.read_html(file_path)
        df = df_list[0]
        print("Read with html")
    except Exception as e2:
        try:
            df = pd.read_csv(file_path, sep='\t', encoding='latin1')
            print("Read with csv/tsv")
        except Exception as e3:
            print(f"Error reading with xlrd: {e}")
            print(f"Error reading with html: {e2}")
            print(f"Error reading with csv: {e3}")
            sys.exit(1)

print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
print("First 30 rows:")
print(df.head(30).to_string())
