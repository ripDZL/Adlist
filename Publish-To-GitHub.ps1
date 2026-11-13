# Create a draft review branch through the user's GitHub CLI login. Never merges.
# SPDX-License-Identifier: GPL-3.0-or-later
[CmdletBinding()]
param([string]$Repository = 'ripDZL/Adlist')
$ErrorActionPreference = 'Stop'
if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw 'Use owner/name.' }
foreach ($command in @('git.exe','gh.exe')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "$command is required." }
}
& gh.exe auth status
if ($LASTEXITCODE -ne 0) { throw 'Sign in using gh auth login, then rerun.' }
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Build-Adlist.ps1') -Verify
if ($LASTEXITCODE -ne 0) { throw 'A complete, verified 31-source build is required before publishing.' }
$files = @('README.md','START-HERE.txt','AUDIT.md','SOURCES.md','CHANGELOG.md','LICENSE','.gitignore','Docs/PROJECT_STATE.md','sources.json','original_sources.json','allowlist.txt','blocklist.txt','build_adlist.py','pipeline_core.py','coverage_audit.py','audit_existing.py','Build-Adlist.ps1','Build-Adlist.cmd','Prepare-Existing-Build.cmd','Audit-Existing-Build.cmd','Install-Daily-Task.ps1','Publish-To-GitHub.ps1','tests/test_builder.py','tests/test_all_sources.py','tests/test_coverage_audit.py','DOMAIN-REVIEW.md','Docs/domain-sample-findings.json','router/install-rb5009-local.rsc.in','router/status.rsc','router/remove-adlist-v2.rsc','.github/workflows/build-adlist.yml','merged_hosts.txt','merged_hosts.sha256','expected_names.txt','suffix_domains.txt','source-audit.csv','stats.json')
$files += @('merged_hosts.txt.gz','coverage-audit.json','source-overlap.csv','domain-review.csv.gz')
foreach ($file in $files) {
    $path = Join-Path $PSScriptRoot $file
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing file: $file. Complete a successful build first." }
    if ((Get-Item -LiteralPath $path).Length -ge 100000000) { throw "$file exceeds the GitHub file limit; full local output is retained." }
}
$accountJson = & gh.exe api user
if ($LASTEXITCODE -ne 0) { throw 'Could not read the authenticated identity.' }
$account = $accountJson | ConvertFrom-Json
$commitName = [string]$account.login
$commitEmail = [string]$account.id + '+' + $commitName + '@users.noreply.github.com'
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$checkoutPath = Join-Path $env:TEMP ('Adlist-All31-Review-' + $runId)
$branch = 'adlist-all31-' + $runId
& gh.exe repo clone $Repository $checkoutPath -- --depth=1
if ($LASTEXITCODE -ne 0) { throw 'Repository clone failed.' }
Push-Location -LiteralPath $checkoutPath
try {
    & git.exe switch -c $branch
    if ($LASTEXITCODE -ne 0) { throw 'Branch creation failed.' }
    foreach ($file in $files) {
        $destination = Join-Path $checkoutPath $file
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination $destination -Force
    }
    & git.exe add -- @files
    if ($LASTEXITCODE -ne 0) { throw 'Staging failed.' }
    & git.exe diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { Write-Host 'Repository already contains this build.'; return }
    if ($LASTEXITCODE -ne 1) { throw 'Could not inspect staged changes.' }
    & git.exe -c ('user.name=' + $commitName) -c ('user.email=' + $commitEmail) commit -m 'Restore all 31 feeds with complete-source validation and bounded router deployment'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed.' }
    & git.exe push -u origin $branch
    if ($LASTEXITCODE -ne 0) { throw 'Push failed; review checkout retained.' }
    $bodyPath = Join-Path $checkoutPath 'PR_BODY_LOCAL.txt'
    $body = @'
Restore the original 31 feed URLs and retain every accepted DNS-name contribution in the complete deduplicated union. Replace URL-based parser guessing with explicit hosts/ABP handling, source-local exceptions, disabled rules, and an audit of browser rules that cannot be expressed in DNS.

Failed, incomplete, malformed or suspicious required sources retain the previous publication. A router budget refusal retains the complete PC list and generates an installer that refuses deployment, rather than truncating coverage. Router updates load one full list at a time, validate its imported count and attempt a bounded rollback from the retained previous local file. Live RouterOS dry-run and resource validation remain required.

Includes interruption/recovery and completeness tests, source hashes/counts, Windows launchers, and a daily workflow that verifies all required sources before committing output. RouterOS scripts receive lexical/manual review, not hardware execution. This is a draft PR and does not merge main.
'@
    [System.IO.File]::WriteAllText($bodyPath,$body,[System.Text.UTF8Encoding]::new($false))
    & gh.exe pr create --repo $Repository --head $branch --base main --draft --title 'Restore all 31 adlist sources with validated resource limits' --body-file $bodyPath
    if ($LASTEXITCODE -ne 0) { throw "Draft PR creation failed; branch $branch is retained." }
    Write-Host "Draft PR created; review checkout: $checkoutPath"
} finally {
    Pop-Location
}
