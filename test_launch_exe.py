import subprocess
import time
import socket
import os
import sys

exe = r'd:\Projeto geral\People analytics - GP\dist\FrequenciaDiaria\FrequenciaDiaria.exe'
cwd = r'd:\Projeto geral\People analytics - GP\dist\FrequenciaDiaria'

print("Launching EXE:", exe)
try:
    proc = subprocess.Popen([exe], cwd=cwd, creationflags=0x00000008, close_fds=True)
    print("Launched PID:", proc.pid)
except Exception as e:
    print("ERROR LAUNCHING EXE:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    for i in range(15):
        time.sleep(1)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        res = s.connect_ex(('127.0.0.1', 5008))
        s.close()
        if res == 0:
            print(f"Port 5008 OPEN at second {i+1}!")
            break
        else:
            print(f"Sec {i+1}: connect result = {res}")
    else:
        print("Port 5008 did not open within 15 seconds.")
except Exception as e:
    print("LOOP ERROR:", e)
    import traceback
    traceback.print_exc()
