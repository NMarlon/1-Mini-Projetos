@echo off
setlocal
python "%~dp0audit.py" %*
set "EXITCODE=%ERRORLEVEL%"
echo.
pause
exit /b %EXITCODE%
