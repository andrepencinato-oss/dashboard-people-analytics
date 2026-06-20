import urllib.request
import re
import os

try:
    print("Testando resposta do app_desktop.exe...")
    req = urllib.request.Request("http://127.0.0.1:5000/")
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
    
    colab_match = re.search(r'const COLAB = \[(.*?)\];', html, re.DOTALL)
    if colab_match:
        content = colab_match.group(1).strip()
        print(f"COLAB encontrado. Tamanho do conteúdo interno: {len(content)} caracteres.")
        if len(content) == 0:
            print("AVISO: O array COLAB está VAZIO! []")
        else:
            print("O array COLAB CONTÉM DADOS!")
    else:
        print("const COLAB não encontrado no HTML!")

    if os.path.exists("leitura_error_log.txt"):
        print("ARQUIVO DE LOG ENCONTRADO!")
        with open("leitura_error_log.txt", "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("O arquivo leitura_error_log.txt NÃO EXISTE.")

except Exception as e:
    print(f"Erro ao conectar com o exe: {e}")
