param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$Root = Get-Location

$Platform = Join-Path $Root "Platform\Putnam_Platform"

$ArchiveLegacy = Join-Path $Root "Archive\Historical\Putnam_Platform_Legacy"
$ArchiveDecision = Join-Path $ArchiveLegacy "Decision_Engine"
$ArchiveEngines = Join-Path $ArchiveLegacy "engines"
$ArchiveTools = Join-Path $ArchiveLegacy "tools"

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

function Remove-Empty($Path) {
    if (Test-Path $Path) {
        $Children = Get-ChildItem $Path -Force
        if ($Children.Count -eq 0) {
            Write-Host "REMOVE EMPTY DIR: $Path"
            if ($Execute) {
                Remove-Item $Path
            }
        }
    }
}

Write-Host ""
Write-Host "Putnam Platform Legacy Cleanup"
Write-Host "Mode:" ($(if ($Execute) {"EXECUTE"} else {"DRY RUN"}))
Write-Host ""

Move-Safe `
    (Join-Path $Platform "Decision_Engine") `
    $ArchiveDecision

Move-Safe `
    (Join-Path $Platform "engines") `
    $ArchiveEngines

Move-Safe `
    (Join-Path $Platform "tools\Audit_And_Clean_Root.ps1") `
    $ArchiveTools

Move-Safe `
    (Join-Path $Platform "tools\Backup_Putnam_OS.ps1") `
    $ArchiveTools

Move-Safe `
    (Join-Path $Platform "tools\putnam_platform_initializer_v1_0.py") `
    $ArchiveTools

Move-Safe `
    (Join-Path $Platform "tools\Run_Putnam_Capture_capture_v1_backup_20260629_212812.bat") `
    $ArchiveTools

Move-Safe `
    (Join-Path $Platform "tools\Split_Putnam_Work_Session.ps1") `
    $ArchiveTools

Remove-Empty (Join-Path $Platform "docs")
Remove-Empty (Join-Path $Platform "installers")
Remove-Empty (Join-Path $Platform "utilities")

Write-Host ""
Write-Host "Cleanup complete."
Write-Host ""

if (-not $Execute) {
    Write-Host "Run with:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\Tools\cleanup_putnam_platform_legacy.ps1 -Execute"
}
