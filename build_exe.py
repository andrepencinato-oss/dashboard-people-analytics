import os
import sys
import subprocess
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd):
    print(f"Executando: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    print("=== EMPACOTAMENTO PYINSTALLER (SÓ ORGANOGRAMA) ===")
    
    # 1. Install pyinstaller locally if not installed
    try:
        import PyInstaller
        print("PyInstaller ja instalado.")
    except ImportError:
        print("Instalando PyInstaller...")
        run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--noconsole",
        "--name", "OrganogramaTool",
        "--clean",
        "--add-data", f"core;core",
        "--add-data", f"module_organograma;module_organograma",
        "launcher_organograma.py"
    ]
    
    print("\nIniciando build do PyInstaller...")
    run_cmd(cmd)
    
    # 3. Mover para DISTRIBUICAO_FINAL_ORGANOGRAMA e limpar
    distrib_dir = os.path.join(PROJECT_ROOT, "DISTRIBUICAO_FINAL_ORGANOGRAMA")
    if os.path.exists(distrib_dir):
        shutil.rmtree(distrib_dir)
    # Não vamos criar a pasta raiz ainda, vamos mover a pasta do onedir para lá
    
    built_dir = os.path.join(PROJECT_ROOT, "dist", "OrganogramaTool")
    
    if os.path.exists(built_dir):
        shutil.move(built_dir, distrib_dir)
        print(f"\n[SUCESSO] Distribuicao movida para {distrib_dir}")
    else:
        print("\n[ERRO] Pasta dist/OrganogramaTool nao encontrada!")
        sys.exit(1)
        
    # Clean PyInstaller temp folders
    shutil.rmtree(os.path.join(PROJECT_ROOT, "build"), ignore_errors=True)
    shutil.rmtree(os.path.join(PROJECT_ROOT, "dist"), ignore_errors=True)
    if os.path.exists("OrganogramaTool.spec"):
        os.remove("OrganogramaTool.spec")
        
    # 4. Criar LEIA-ME.txt
    readme_path = os.path.join(distrib_dir, "LEIA-ME.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write(" SISTEMA PEOPLE ANALYTICS - MODULO ORGANOGRAMA\n")
        f.write("="*50 + "\n\n")
        f.write("Instruções de Acesso:\n")
        f.write("1. Clique duas vezes no arquivo 'OrganogramaTool.exe'.\n")
        f.write("2. O sistema irá iniciar silenciosamente em background.\n")
        f.write("3. Aguarde alguns segundos. O seu navegador abrirá automaticamente o sistema.\n\n")
        f.write("Nota: O sistema é conectado à nuvem e receberá atualizações automáticas silenciosas sempre que houver novidades.\n")
        
    # 5. Zip the distrib directory for easy sharing
    shutil.make_archive(distrib_dir, 'zip', distrib_dir)
        
    print(f"\n[Empacotamento Concluido] Arquivo {distrib_dir}.zip pronto.")

if __name__ == "__main__":
    main()
