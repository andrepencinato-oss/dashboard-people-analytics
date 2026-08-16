import sys
sys.path.insert(0, r'd:\Projeto geral\People analytics - GP\module_frequencia_diaria')
from app_frequencia import load_acesso_config
config = load_acesso_config()
print('Users:')
for u in config.get('usuarios', []):
    print(f"- {u['login']}")
