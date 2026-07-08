$ErrorActionPreference = "Stop"

if (-not $env:USERENVIRONMENT -or -not (Test-Path $env:USERENVIRONMENT)) {
    $env:USERENVIRONMENT = Join-Path $env:USERPROFILE "OneDrive\PutnamCollectibles"
}

$root = $env:USERENVIRONMENT
$os = Join-Path $root "Putnam_OS"
$archive = Join-Path $os "System_Archive"
New-Item -ItemType Directory -Force -Path $archive | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$zip = Join-Path $archive "Putnam_OS_Backup_$stamp.zip"

Compress-Archive -Path (Join-Path $os "*") -DestinationPath $zip -Force

Write-Host "Backup created:"
Write-Host $zip
pause

