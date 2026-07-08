param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$Root = Get-Location

$PutnamOS = Join-Path $Root "Platform\Putnam_OS"

$ArchiveLogs = Join-Path $Root "Archive\Historical\Putnam_OS_Logs"
$ArchiveSystem = Join-Path $Root "Archive\Historical\Putnam_OS_System_Archive"
$ArchivePatch = Join-Path $Root "Archive\Historical\Putnam_OS_Patch_Source"
$DataCompleted = Join-Path $Root "Data\Completed_Jobs"
$DataExports = Join-Path $Root "Data\Exports"

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
Write-Host "Putnam OS Cleanup"
Write-Host "Mode:" ($(if ($Execute) {"EXECUTE"} else {"DRY RUN"}))
Write-Host ""

# Historical logs
Move-Safe `
    (Join-Path $PutnamOS "System\logs\Decision_Engine_Log_20260628_084811.txt") `
    $ArchiveLogs

Move-Safe `
    (Join-Path $PutnamOS "System\logs\patch_3_2_1_20260626_224737.log") `
    $ArchiveLogs

Move-Safe `
    (Join-Path $PutnamOS "System\logs\pricing_20260626_112934.log") `
    $ArchiveLogs

# Archived system snapshot
Move-Safe `
    (Join-Path $PutnamOS "System_Archive") `
    $ArchiveSystem

# Patch source snapshot
Move-Safe `
    (Join-Path $PutnamOS "putnam_os_source_for_patch.zip") `
    $ArchivePatch

# Completed jobs output
Move-Safe `
    (Join-Path $PutnamOS "Completed Jobs") `
    $DataCompleted

# Inventory snapshot export
Move-Safe `
    (Join-Path $PutnamOS "System\data\carduploader_inventory_snapshot.csv") `
    $DataExports

Write-Host ""
Write-Host "Cleanup complete."
Write-Host ""

if (-not $Execute) {
    Write-Host "Run with:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\Tools\cleanup_putnam_os.ps1 -Execute"
}
