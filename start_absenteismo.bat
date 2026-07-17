@echo off
cd /d "%~dp0"
echo Iniciando o Dashboard de Absenteismo (Porta 5006)...
py -3 module_absenteismo_turnover/app_absenteismo.py
pause
