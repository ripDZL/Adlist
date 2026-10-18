@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Build-Adlist.ps1" %*
set "buildResult=%ERRORLEVEL%"
echo.
if not "%buildResult%"=="0" echo Build failed. Read the error above.
pause
exit /b %buildResult%
