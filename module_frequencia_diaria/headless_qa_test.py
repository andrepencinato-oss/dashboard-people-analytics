import subprocess
import time
import urllib.request
import psutil

exe_path = r"D:\Projeto geral\People analytics - GP\module_frequencia_diaria\FrequenciaDiaria.exe"
print(f"Starting {exe_path}...")
proc = subprocess.Popen([exe_path])

time.sleep(5) # wait for server to start

try:
    print("Testing connection to http://localhost:5008/login")
    response = urllib.request.urlopen("http://localhost:5008/login", timeout=10)
    print(f"HTTP Status Code: {response.getcode()}")
    print("Server is UP and responding!")
except Exception as e:
    print(f"Failed to connect: {e}")

# Kill the process and any children
def kill_proc_tree(pid, including_parent=True):    
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        if including_parent:
            parent.kill()
    except psutil.NoSuchProcess:
        pass

kill_proc_tree(proc.pid)
print("Process terminated.")
