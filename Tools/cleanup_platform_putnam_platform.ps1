param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$Root = Get-Location

$Source = Join-Path $Root "Platform\Putnam_Platform"

$Archive = Join-Path $Root "Archive\Historical\Putnam_Platform_Backups"
$Reports = Join-Path $Root "Docs\Reports"

function Ensure-Dir($Path) {
    if (-not (Test-Path $Path)) {
        if ($Execute) {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
        }
        Write-Host "CREATE DIR: $Path"
    }
}

function Move-Safe($Path, $Destination) {
    if (Test-Path $Path) {

        Ensure-Dir $Destination

        $Name = Split-Path $Path -Leaf
        $Target = Join-Path $Destination $Name

        if ($Execute) {
            Move-Item $Path $Target
        }

        Write-Host "MOVE:"
        Write-Host "  $Path"
        Write-Host "  -> $Target"
    }
}

Write-Host ""
Write-Host "Putnam_Platform Cleanup"
Write-Host "Mode:" ($(if ($Execute) {"EXECUTE"} else {"DRY RUN"}))
Write-Host ""

$Capture = Join-Path $Source "capture"

Get-ChildItem $Capture -Directory -Filter "backup_*" -ErrorAction SilentlyContinue |
ForEach-Object {
    Move-Safe $_.FullName $Archive
}

Move-Safe `
    (Join-Path $Capture "Putnam_Capture_v0_1_backup.py") `
    $Archive

$Docs = Join-Path $Source "docs"

Get-ChildItem $Docs -File -Filter "platform_initializer_report_*" -ErrorAction SilentlyContinue |
ForEach-Object {
    Move-Safe $_.FullName $Reports
}

Write-Host ""
Write-Host "Cleanup preview complete."
Write-Host ""

if (-not $Execute) {
    Write-Host "Run with:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\Tools\cleanup_platform_putnam_platform.ps1 -Execute"
}
