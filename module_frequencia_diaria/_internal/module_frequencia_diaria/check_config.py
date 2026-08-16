import sys, json
sys.path.insert(0, r'd:\Projeto geral\People analytics - GP\module_frequencia_diaria')
from app_frequencia import load_acesso_config
config = load_acesso_config()
for u in config.get('usuarios', []):
    print(f"Login: {u['login']}")
    senha = u.get('senha', 'N/A')
    print(f"  Senha: {senha[:20]}..." if len(senha) > 20 else f"  Senha: {senha}")
    print(f"  Admin: {u.get('admin', False)}")
    print(f"  Gestor: {u.get('gestor', False)}")
    print(f"  Ativo: {u.get('ativo', True)}")
    print()
