@echo off
echo ========================================================
echo   Instalador: Servidor Absenteismo_plug (Background)
echo ========================================================
echo.

:: Verifica se esta rodando como Administrador para regras de Firewall
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Permissao de Administrador detectada.
    echo Liberando porta 5008 no Windows Firewall...
    netsh advfirewall firewall add rule name="Absenteismo_plug_Server_5008" dir=in action=allow protocol=TCP localport=5008 >nul 2>&1
    echo [OK] Firewall configurado.
) else (
    echo [AVISO] Execute este arquivo como Administrador se o Firewall bloquear a porta 5008.
)

echo.
echo Copiando script de inicializacao para o Startup do Windows...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Cria um script temporário VBS para gerar o atalho corretamente
set "VBS_TEMP=%TEMP%\CreateShortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_TEMP%"
echo sLinkFile = "%STARTUP_FOLDER%\Absenteismo_plug.lnk" >> "%VBS_TEMP%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_TEMP%"
echo oLink.TargetPath = "%~dp0iniciar_servidor.vbs" >> "%VBS_TEMP%"
echo oLink.WorkingDirectory = "%~dp0" >> "%VBS_TEMP%"
echo oLink.Description = "Inicializador do Absenteismo_plug" >> "%VBS_TEMP%"
echo oLink.Save >> "%VBS_TEMP%"

cscript //nologo "%VBS_TEMP%"
del "%VBS_TEMP%"

echo.
echo [SUCESSO] O sistema agora iniciara automaticamente com o Windows!
echo O servidor estara disponivel na rede local pelo seu Hostname.
echo.
pause
