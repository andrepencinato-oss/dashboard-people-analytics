import pandas as pd
import os

file_path = r"D:\Projeto geral\People analytics - GP\module_absenteismo_turnover\Absenteismo 25_26.XLS"
out_path = r"D:\Projeto geral\People analytics - GP\module_absenteismo_turnover\tabulado_absenteismo.txt"

df = pd.read_excel(file_path, engine='xlrd')
df = df.fillna('')

current_cod = ""
current_nome = ""
current_escala_raw = ""
current_escala_times = ""

output = []

for index, row in df.iterrows():
    col0 = str(row.iloc[0]).strip()
    col1 = str(row.iloc[1]).strip()
    col2 = str(row.iloc[2]).strip()
    col3 = str(row.iloc[3]).strip()
    col4 = str(row.iloc[4]).strip()
    col5 = str(row.iloc[5]).strip() if len(row) > 5 else ""

    if not col0:
        continue

    # Colaborador (Ex: '410', 'LETICIA BERGAMO ANTONIO')
    if col0.isdigit() and col1 != "" and col2 == "" and "Total" not in col0:
        current_cod = col0
        current_nome = col1
        continue

    # Escala (Ex: '36', '1', '1', '07:00 11:00 12:30 17:18')
    if col0.isdigit() and col3 != "" and ":" in col3 and len(col3.split()) >= 2 and col4 == "":
        current_escala_raw = col0.zfill(4)
        current_escala_times = col3
        continue

    # Date row (Ex: '29/01/25', 'Qua', '06:55 13:13 17:18', '999', 'Marcações Inválidas')
    if len(col0) == 8 and col0.count('/') == 2:
        data = col0
        dia = col1
        marcacoes_raw = col2
        sit_cod = col3
        sit_desc = col4
        horas = col5
        
        # Format Escala
        escala_parts = current_escala_times.split()
        if len(escala_parts) == 4:
            escala_str = f"{current_escala_raw} entrada {escala_parts[0]} almoço {escala_parts[1]} às {escala_parts[2]} saída {escala_parts[3]}"
        elif len(escala_parts) == 2:
            escala_str = f"{current_escala_raw} entrada {escala_parts[0]} saída {escala_parts[1]}"
        else:
            escala_str = f"{current_escala_raw} {current_escala_times}"

        # Format Marcações
        marc_parts = marcacoes_raw.split()
        if len(marc_parts) == 4:
            marc_str = f"entrada {marc_parts[0]} almoço {marc_parts[1]} {marc_parts[2]} saída {marc_parts[3]}"
        elif len(marc_parts) == 3:
             marc_str = f"entrada {marc_parts[0]} almoço {marc_parts[1]} {marc_parts[2]} saída Não marcou"
        elif len(marc_parts) == 2:
            marc_str = f"entrada {marc_parts[0]} saída {marc_parts[1]}"
        elif len(marc_parts) == 1:
            marc_str = f"entrada {marc_parts[0]}"
        elif len(marc_parts) == 0:
            marc_str = "Não marcou"
        else:
            marc_str = " ".join(marc_parts)

        block = (
            f"data {data}\n"
            f"Dia: {dia}\n"
            f"Cod. {current_cod}\n"
            f"Nome: {current_nome}\n"
            f"Escala: {escala_str}\n"
            f"Marcação: {marc_str}\n"
            f"Situação Apurada :{sit_cod} {sit_desc}\n"
            f"Horas: {horas}\n"
            f"{'-'*40}"
        )
        output.append(block)

with open(out_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(output))

print(f"Total de {len(output)} registros extraídos com sucesso em {out_path}.")
