@echo off
echo ========================================================
echo   Instalador: Servidor Controle de Vagas (Background)
echo ========================================================
echo.

:: Verifica se esta rodando como Administrador para regras de Firewall
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Permissao de Administrador detectada.
    echo Liberando porta 5000 no Windows Firewall...
    netsh advfirewall firewall add rule name="Controle_Vagas_Server_5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
    echo [OK] Firewall configurado para porta 5000.
) else (
    echo [AVISO] Execute este arquivo como Administrador se o Firewall bloquear a porta 5000.
)

echo.
echo Copiando script de inicializacao para o Startup do Windows...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Cria um script temporario VBS para gerar o atalho corretamente
set "VBS_TEMP=%TEMP%\CreateShortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_TEMP%"
echo sLinkFile = "%STARTUP_FOLDER%\Controle_Vagas.lnk" >> "%VBS_TEMP%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_TEMP%"
echo oLink.TargetPath = "%~dp0iniciar_servidor.vbs" >> "%VBS_TEMP%"
echo oLink.WorkingDirectory = "%~dp0" >> "%VBS_TEMP%"
echo oLink.Description = "Inicializador do Controle de Vagas" >> "%VBS_TEMP%"
echo oLink.Save >> "%VBS_TEMP%"

cscript //nologo "%VBS_TEMP%"
del "%VBS_TEMP%"

echo.
echo [SUCESSO] O sistema agora iniciara automaticamente com o Windows!
echo O servidor estara disponivel na rede local pelo seu Hostname na porta 5000.
echo.
pause
