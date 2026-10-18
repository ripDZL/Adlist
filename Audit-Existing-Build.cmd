@echo off
setlocal
if "%~1"=="" (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Build-Adlist.ps1" -AuditExisting
) else (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Build-Adlist.ps1" -AuditExisting -ReuseBuild "%~1"
)
set "auditResult=%ERRORLEVEL%"
echo.
if not "%auditResult%"=="0" echo Audit failed. Read the error above. The original build is retained.
pause
exit /b %auditResult%
