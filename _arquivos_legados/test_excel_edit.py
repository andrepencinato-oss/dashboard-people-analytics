import pandas as pd
import sys

try:
    # First try reading it as an actual excel file
    df = pd.read_excel('DP_-_Colaboradores_-_Extrato_Diário.xlsx', header=0)
    print("Read as EXCEL successfully. Shape:", df.shape)
    
    # User said: "na ultima linha na coluna A700 eu coloquei um x troque por eu estou aqui"
    # Find cell with 'x'
    for i, row in df.iterrows():
        if 'x' in [str(x).strip().lower() for x in row.values]:
            print(f"Found 'x' at index {i}")
            
    # Actually, we can just replace 'x' with 'eu estou aqui' in the last row
    # The user said column A700 (which is column index 0)
    last_row_idx = df.index[-1]
    print(f"Last row index: {last_row_idx}")
    print(f"Col A value: {df.iloc[-1, 0]}")
    
    if str(df.iloc[-1, 0]).strip().lower() == 'x':
        df.iloc[-1, 0] = 'eu estou aqui'
        print("Replaced!")
    else:
        # Check if it's anywhere near the last row in Col A
        for i in range(max(0, len(df)-10), len(df)):
            if str(df.iloc[i, 0]).strip().lower() == 'x':
                df.iloc[i, 0] = 'eu estou aqui'
                print(f"Replaced at index {i} instead!")
                break
                
    df.to_excel('DP_-_Colaboradores_-_Extrato_Diário.xlsx', index=False)
    print("Saved!")
    
except Exception as e:
    import traceback
    traceback.print_exc()
