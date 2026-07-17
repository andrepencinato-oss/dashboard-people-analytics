@echo off
cd /d "d:\Projeto geral\People analytics - GP"
echo Starting... > server_debug.log
py -3 module_controle_vagas/app_vagas.py >> server_debug.log 2>&1
echo Exited with code %errorlevel% >> server_debug.log
pause
