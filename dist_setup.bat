@echo off
echo ==============================================
echo   People Analytics Frequencia Diaria - Instalador de Distribuicao
echo ==============================================
echo.

echo Verificando instalacao do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Python nao foi encontrado no PATH. 
    echo O aplicativo principal foi compilado e nao precisa do Python,
    echo mas alguns modulos auxiliares ou o atualizador OTA podem precisar.
    echo Por favor, instale o Python 3.10+ do Microsoft Store.
    echo.
) else (
    echo [OK] Python detectado.
)

echo.
echo Criando estrutura de dados local...
if not exist "dist\PeopleAnalyticsFrequenciaDiaria\data" mkdir "dist\PeopleAnalyticsFrequenciaDiaria\data"
if not exist "dist\PeopleAnalyticsFrequenciaDiaria\module_frequencia_diaria\data" mkdir "dist\PeopleAnalyticsFrequenciaDiaria\module_frequencia_diaria\data"
if not exist "dist\PeopleAnalyticsFrequenciaDiaria\module_absenteismo_turnover\data" mkdir "dist\PeopleAnalyticsFrequenciaDiaria\module_absenteismo_turnover\data"
echo [OK] Pastas de dados criadas.

echo.
echo ==============================================
echo Instalacao concluida!
echo Para iniciar, execute: dist\PeopleAnalyticsFrequenciaDiaria\PeopleAnalyticsFrequenciaDiaria.exe
echo ==============================================
pause
