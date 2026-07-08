param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$Root = Get-Location

$Marketplace = Join-Path $Root "Platform\Marketplace_Intelligence"

$ArchiveBackups = Join-Path $Root "Archive\Historical\Marketplace_Intelligence_Backups"
$ArchiveReports = Join-Path $Root "Archive\Historical\Marketplace_Intelligence_Reports"

function Ensure-Dir($Path) {
    if (-not (Test-Path $Path)) {
        Write-Host "CREATE DIR: $Path"
        if ($Execute) {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
        }
    }
}

function Move-Safe($Source, $Destination) {
    if (Test-Path $Source) {
        Ensure-Dir $Destination

        $Target = Join-Path $Destination (Split-Path $Source -Leaf)

        Write-Host "MOVE:"
        Write-Host "  $Source"
        Write-Host "  -> $Target"

        if ($Execute) {
            Move-Item $Source $Target
        }
    }
}

Write-Host ""
Write-Host "Marketplace Intelligence Cleanup"
Write-Host "Mode:" ($(if ($Execute) {"EXECUTE"} else {"DRY RUN"}))
Write-Host ""

Move-Safe `
    (Join-Path $Marketplace "backups") `
    $ArchiveBackups

Move-Safe `
    (Join-Path $Marketplace "reports") `
    $ArchiveReports

Write-Host ""
Write-Host "Cleanup complete."
Write-Host ""

if (-not $Execute) {
    Write-Host "Run with:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\Tools\cleanup_marketplace_intelligence.ps1 -Execute"
}
