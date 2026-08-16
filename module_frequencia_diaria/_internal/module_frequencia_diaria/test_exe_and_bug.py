import subprocess
import time
import socket
import os
import sys

exe = r'D:\Projeto geral\People analytics - GP\module_frequencia_diaria\dist\Absenteismo_plug\Absenteismo_plug.exe'
cwd = r'D:\Projeto geral\People analytics - GP\module_frequencia_diaria\dist\Absenteismo_plug'

print('Launching EXE...')
proc = subprocess.Popen([exe], cwd=cwd, creationflags=0x00000008, close_fds=True)

try:
    port_open = False
    for i in range(15):
        time.sleep(1)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        res = s.connect_ex(('127.0.0.1', 5008))
        s.close()
        if res == 0:
            port_open = True
            print('Port 5008 OPEN!')
            break

    if port_open:
        print('Running qa_test_bug.py...')
        qa_proc = subprocess.run([sys.executable, r'D:\Projeto geral\People analytics - GP\module_frequencia_diaria\qa_test_bug.py'], capture_output=True, text=True)
        print('--- QA TEST OUTPUT ---')
        print(qa_proc.stdout)
        print('--- QA TEST ERROR ---')
        print(qa_proc.stderr)
finally:
    print('Killing EXE...')
    proc.kill()
