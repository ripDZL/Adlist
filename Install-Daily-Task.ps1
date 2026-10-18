# Optional LOCAL file generation. Does not upload to the router or GitHub.
# SPDX-License-Identifier: GPL-3.0-or-later
[CmdletBinding()]
param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$taskName = 'ripDZL-Adlist-Daily'
if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host 'Daily task removed.'
    exit
}
$scriptPath = Join-Path $PSScriptRoot 'Build-Adlist.ps1'
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw 'Extract the entire package before installing the task.' }
$arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $scriptPath + '"'
$action = New-ScheduledTaskAction -Execute (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Argument $arguments -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At '06:15'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -RestartCount 1 -RestartInterval (New-TimeSpan -Minutes 30)
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Build bounded RouterOS hosts locally. No upload or network configuration changes.' -Force | Out-Null
Write-Host 'Daily task installed for 6:15 AM local time, while this Windows user is signed in.'
Write-Host 'This only regenerates local files. Use the GitHub workflow for hosted daily updates.'
