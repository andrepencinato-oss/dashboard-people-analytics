import re

filepath = r"D:\Projeto geral\People analytics - GP\module_absenteismo_turnover\tabulado_absenteismo.txt"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

blocks = content.split('----------------------------------------')

total_minutes = 0
count = 0
print("Registros de Leticia (Cod 410) - Situação 101:")

for block in blocks:
    if not block.strip():
        continue
    
    # Check conditions
    if "Cod. 410" in block and "101 Saída Antecipada" in block:
        print(block.strip())
        print("-" * 20)
        
        # Extract hours
        match = re.search(r"Horas:\s*(\d{2,3}):(\d{2})", block)
        if match:
            h = int(match.group(1))
            m = int(match.group(2))
            total_minutes += (h * 60) + m
            count += 1

hours = total_minutes // 60
minutes = total_minutes % 60

print(f"\nTotal de registros encontrados: {count}")
print(f"Total de horas somadas: {hours:02d}:{minutes:02d}")
