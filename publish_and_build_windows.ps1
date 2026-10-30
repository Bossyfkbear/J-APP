# Audio Post Toolkit - authenticated upload and Windows Actions build.
# Run only after reviewing this source. No personal access token is stored here.
[CmdletBinding()]
param([switch]$SkipWatch)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$repo = 'Bossyfkbear/J-APP'
$repoUrl = 'https://github.com/Bossyfkbear/J-APP.git'
$workflow = 'windows-build.yml'

function Test-LastCommand([string]$name) {
    if ($LASTEXITCODE -ne 0) { throw "$name failed (exit code $LASTEXITCODE)." }
}

foreach ($program in @('git','gh')) {
    if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
        throw "Missing $program. Install Git for Windows and GitHub CLI first. See GITHUB_UPLOAD.md."
    }
}
if (-not (Test-Path '.github/workflows/windows-build.yml' -PathType Leaf)) {
    throw 'Run this script in the complete AudioPostToolkit source folder.'
}

# Windows PowerShell 5.1 may turn native stderr into a terminating error.
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try { & gh auth status --hostname github.com *> $null } finally { $ErrorActionPreference = $previousPreference }
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Please complete the GitHub CLI browser sign-in (no token pasted into this script).'
    & gh auth login --hostname github.com --git-protocol https --web
    Test-LastCommand 'gh auth login'
}
$login = (& gh api user --jq '.login').Trim()
Test-LastCommand 'gh api user'
if ($login -ne 'Bossyfkbear') {
    throw "Current GitHub CLI login is '$login', not 'Bossyfkbear'. Run: gh auth switch --hostname github.com --user Bossyfkbear"
}
$repoInfo = & gh api "repos/$repo" | ConvertFrom-Json
Test-LastCommand 'gh api repository'
if (-not $repoInfo.permissions.push) { throw "Your GitHub account does not have push access to $repo." }
if ($repoInfo.private -eq $false) {
    Write-Host 'Notice: J-APP is PUBLIC; committed source files will be publicly visible.'
}

if (-not (Test-Path '.git' -PathType Container)) {
    & git init -b main
    Test-LastCommand 'git init'
}
$branch = (& git branch --show-current).Trim()
Test-LastCommand 'git branch'
if ($branch -ne 'main') { throw "Expected local main branch, found '$branch'. Stopping without changing it." }
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try { $origin = (& git remote get-url origin 2>$null) } finally { $ErrorActionPreference = $previousPreference }
if ($LASTEXITCODE -ne 0) {
    & git remote add origin $repoUrl
    Test-LastCommand 'git remote add'
} elseif ($origin.Trim() -ne $repoUrl) {
    throw "Unexpected origin: $origin. Expected $repoUrl. Refusing to push."
}
& gh auth setup-git
Test-LastCommand 'gh auth setup-git'
& git add --all
Test-LastCommand 'git add'
& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    $userId = (& gh api user --jq '.id').Trim()
    Test-LastCommand 'gh api user id'
    $email = "$userId+$login@users.noreply.github.com"
    & git -c "user.name=$login" -c "user.email=$email" commit -m 'Add Audio Post Toolkit Windows build source'
    Test-LastCommand 'git commit'
}
# Never force-push. A remote history mismatch stops safely.
& git push --set-upstream origin main
Test-LastCommand 'git push'
Write-Host "Uploaded: https://github.com/$repo"

# Workflow registration can lag a new repository's first push.
$dispatched = $false
for ($attempt=1; $attempt -le 8; $attempt++) {
    & gh workflow run $workflow --repo $repo --ref main
    if ($LASTEXITCODE -eq 0) { $dispatched = $true; break }
    Start-Sleep -Seconds 4
}
if (-not $dispatched) {
    throw "Source push succeeded but workflow dispatch failed. Open https://github.com/$repo/actions and run Windows development build manually."
}
Write-Host "Build requested: https://github.com/$repo/actions"
if ($SkipWatch) { return }

$runId = ''
for ($attempt=1; $attempt -le 12; $attempt++) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $runId = (& gh run list --repo $repo --workflow $workflow --event workflow_dispatch --branch main --limit 1 --json databaseId --jq '.[0].databaseId' 2>$null) } finally { $ErrorActionPreference = $previousPreference }
    if ($LASTEXITCODE -eq 0 -and $runId -match '^\d+$') { break }
    Start-Sleep -Seconds 5
}
if ($runId -notmatch '^\d+$') {
    throw "Workflow queued but the run ID is not visible yet. Find it at https://github.com/$repo/actions."
}
Write-Host "Watching Windows build run $runId..."
& gh run watch $runId --repo $repo --exit-status
Test-LastCommand 'Windows GitHub Actions build'
$output = Join-Path $PSScriptRoot 'windows-build-artifact'
New-Item -ItemType Directory -Force -Path $output | Out-Null
& gh run download $runId --repo $repo --name AudioPostToolkit-Windows-Development --dir $output
Test-LastCommand 'gh run download'
Write-Host "Windows development ZIP and SHA256: $output"
Write-Host 'EXE device playback, optional AI, and audio-quality listening still need real Windows verification.'
