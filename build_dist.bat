@echo off
echo Iniciando build do PyInstaller (onedir)...
py -m PyInstaller --noconfirm --name PeopleAnalyticsFrequenciaDiaria --onedir ^
  --add-data "module_frequencia_diaria/*.html;module_frequencia_diaria" ^
  --add-data "module_absenteismo_turnover/*.html;module_absenteismo_turnover" ^
  --add-data "module_people_analytics/*.html;module_people_analytics" ^
  --add-data "module_sst/*.html;module_sst" ^
  --add-data "core/*;core" ^
  main_launcher.py

echo.
echo Build concluido!
