@echo off
setlocal
cd /d "%~dp0"
title Terabox Auto-Backuper - Iniciar

set "APP_URL=http://127.0.0.1:8765"
set "APP_PORT=8765"

REM Se o app ja estiver rodando, apenas abre o navegador.
netstat -ano | findstr /R /C:":%APP_PORT% .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo O aplicativo ja esta rodando. Abrindo no navegador...
    start "" "%APP_URL%"
    exit /b 0
)

REM Verifica se o Python existe.
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERRO] Python nao encontrado no seu computador.
    echo Instale o Python em https://www.python.org/downloads/
    echo IMPORTANTE: marque a opcao "Add Python to PATH" na instalacao.
    echo.
    pause
    exit /b 1
)

REM Verifica as dependencias; instala se faltar alguma.
python -c "import fastapi, uvicorn, httpx, aiosqlite, watchdog, apscheduler, winotify" >nul 2>&1
if errorlevel 1 (
    echo Primeira execucao detectada. Instalando dependencias...
    echo Isso pode levar alguns minutos. Aguarde...
    echo.
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERRO] Falha ao instalar dependencias.
        echo Verifique sua conexao com a internet e tente novamente.
        pause
        exit /b 1
    )
    echo.
    echo Dependencias instaladas com sucesso!
)

REM Inicia o servidor em segundo plano, sem janela de console.
where pythonw >nul 2>&1
if errorlevel 1 (
    start "Terabox Auto-Backuper" /min python app.py
) else (
    start "Terabox Auto-Backuper" pythonw app.py
)

REM Aguarda o servidor iniciar (ate 30 segundos) e abre o navegador.
echo Iniciando o Terabox Auto-Backuper...
set /a tries=0
:waitloop
netstat -ano | findstr /R /C:":%APP_PORT% .*LISTENING" >nul 2>&1
if not errorlevel 1 goto started
set /a tries+=1
if %tries% GEQ 30 goto started
ping -n 2 127.0.0.1 >nul
goto waitloop
:started
start "" "%APP_URL%"

echo.
echo Pronto! O aplicativo esta rodando em %APP_URL%
echo Para parar, use o arquivo PARAR.bat
ping -n 4 127.0.0.1 >nul
exit /b 0