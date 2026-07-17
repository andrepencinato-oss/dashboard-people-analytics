import os
import sys
import pandas as pd
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(current_dir, 'core')
sys.path.insert(0, core_dir)

from drive_sync import auto_upload_to_drive

def extract_and_upload():
    print("[Pipeline] Iniciando extração do Senior (Mock)...")
    time.sleep(1)
    
    # Pasta de entrada/saída simulada
    output_dir = os.path.join(current_dir, 'module_frequencia_diaria', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    # Gerando um arquivo mock processado
    df = pd.DataFrame({
        "matricula": [101, 102, 103],
        "nome": ["Alice", "Bob", "Charlie"],
        "setor": ["TI", "RH", "Vendas"],
        "situacao": ["Falta", "Atraso", "Falta"]
    })
    
    file_name = "extrato_senior_processado_teste.csv"
    file_path = os.path.join(output_dir, file_name)
    df.to_csv(file_path, sep=';', index=False, encoding='latin1')
    
    print(f"[Pipeline] Arquivo gerado com sucesso: {file_path}")
    
    print("[Pipeline] Acionando auto_upload_to_drive()...")
    file_id = auto_upload_to_drive(file_path)
    
    if file_id:
        print(f"[Pipeline] Ciclo completo! Arquivo subiu para o Drive. ID: {file_id}")
    else:
        print("[Pipeline] Falha no upload automático.")

if __name__ == '__main__':
    extract_and_upload()
