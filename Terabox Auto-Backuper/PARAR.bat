@echo off
setlocal
cd /d "%~dp0"
title Terabox Auto-Backuper - Parar

echo Parando o Terabox Auto-Backuper...

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo.
echo Aplicativo parado.
ping -n 4 127.0.0.1 >nul
exit /b 0