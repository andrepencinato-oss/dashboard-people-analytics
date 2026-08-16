@echo off
ping 127.0.0.1 -n 3 > nul
taskkill /f /im "Absenteismo_plug.exe" > nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5008') do taskkill /f /pid %%a > nul 2>&1
ping 127.0.0.1 -n 2 > nul

del /q /f "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\*.old" > nul 2>&1
ren "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\Absenteismo_plug.exe" "Absenteismo_plug.exe.old" > nul 2>&1
ren "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\*.dll" "*.dll.old" > nul 2>&1
ren "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\*.pyd" "*.pyd.old" > nul 2>&1

xcopy /s /y /q "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\.update_stage\*" "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\"

if exist "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\Absenteismo_plug.exe" (
) else (
    ren "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\Absenteismo_plug.exe.old" "Absenteismo_plug.exe" > nul 2>&1
)

rmdir /s /q "D:\Projeto geral\People analytics - GP\module_frequencia_diaria\.update_stage"
cd /d "D:\Projeto geral\People analytics - GP\module_frequencia_diaria"
start "" "Absenteismo_plug.exe"
del "%~f0"
