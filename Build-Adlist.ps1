# SPDX-License-Identifier: GPL-3.0-or-later
[CmdletBinding()]
param([switch]$DryRun, [switch]$AcceptLargeChange, [switch]$Verify,
      [switch]$PrepareExisting, [string]$ReuseBuild, [switch]$AuditExisting)
$ErrorActionPreference = 'Stop'
try {
    if (($PrepareExisting -or $AuditExisting) -and -not $ReuseBuild) {
        $ReuseBuild = (Read-Host 'Paste the folder containing your completed v3.0.x build (stats.json and merged_hosts.txt)').Trim().Trim('"')
        if (-not $ReuseBuild) { throw 'A completed build folder is required.' }
    }
    if ($ReuseBuild -and ($DryRun -or $Verify -or $AcceptLargeChange)) { throw 'Use reuse by itself; no downloads or change-check bypass is needed.' }
    $pythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    $pythonArguments = @('-3')
    if (-not $pythonCommand) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        $pythonArguments = @()
    }
    if (-not $pythonCommand) { throw 'Python 3.11 or newer is required. Install it from https://www.python.org/downloads/windows/ and run this again.' }
    & $pythonCommand.Source @pythonArguments -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'The selected Python must be version 3.11 or newer.' }
    if ($AuditExisting) {
        if (-not $ReuseBuild) { throw 'A completed build folder is required.' }
        & $pythonCommand.Source @pythonArguments (Join-Path $PSScriptRoot 'audit_existing.py') '--build-folder' $ReuseBuild '--output' (Join-Path $PSScriptRoot 'domain-audit')
        if ($LASTEXITCODE -ne 0) { throw 'Audit failed; the completed build was retained.' }
        Write-Host 'Read domain-audit\coverage-audit.json. Domain review candidates are in domain-review.csv.gz.' -ForegroundColor Green
        exit 0
    }
    $buildArguments = @((Join-Path $PSScriptRoot 'build_adlist.py'), '--output', $PSScriptRoot)
    if ($DryRun) { $buildArguments += '--dry-run' }
    if ($AcceptLargeChange) { $buildArguments += '--accept-large-change' }
    if ($Verify) { $buildArguments += '--verify' }
    if ($ReuseBuild) { $buildArguments += @('--reuse-build', $ReuseBuild) }
    & $pythonCommand.Source @pythonArguments @buildArguments
    if ($LASTEXITCODE -ne 0) { throw "Adlist operation failed (exit $LASTEXITCODE). See build-error.log. A normal build retries any pending publication recovery." }
    if (-not $DryRun) {
        $report = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'stats.json') -Raw | ConvertFrom-Json
        Write-Host ("Complete build: {0} sources; {1:N0} domains." -f $report.source_count, $report.domains) -ForegroundColor Green
        if ($report.router.eligible) {
            Write-Host ("Planned cache: {0} MiB; minimum free RAM before import: {1} MiB." -f $report.router.cache_mib, $report.router.required_free_mib)
            Write-Host 'Read router-ready\INSTALL.txt before uploading the three deployment files.'
        } else {
            Write-Host 'The full list was saved, but it exceeds the router budget. The generated installer will refuse deployment.' -ForegroundColor Yellow
            Write-Host 'Do not force installation. The complete merged_hosts.txt remains available for a DNS server with sufficient resources.'
        }
    }
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
