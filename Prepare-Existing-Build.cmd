@echo off
setlocal
if "%~1"=="" (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Build-Adlist.ps1" -PrepareExisting
) else (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Build-Adlist.ps1" -ReuseBuild "%~1"
)
set "buildResult=%ERRORLEVEL%"
echo.
if not "%buildResult%"=="0" echo Preparation failed. Read the error above. The original build is retained.
pause
exit /b %buildResult%
