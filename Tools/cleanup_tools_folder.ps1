param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$Root = Get-Location
$Tools = Join-Path $Root "Tools"
$ExternalApps = Join-Path $env:USERPROFILE "Applications"
$LosslessDest = Join-Path $ExternalApps "LosslessCut"

function Ensure-Dir($Path) {
    if (-not (Test-Path $Path)) {
        if ($Execute) {
            New-Item -ItemType Directory -Path $Path | Out-Null
        }
        Write-Host "CREATE DIR: $Path"
    }
}

function Move-ItemSafe($Source, $DestinationDir) {
    if (-not (Test-Path $Source)) {
        return
    }

    Ensure-Dir $DestinationDir

    $Name = Split-Path $Source -Leaf
    $Destination = Join-Path $DestinationDir $Name

    if (Test-Path $Destination) {
        $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $Destination = Join-Path $DestinationDir "$Name.moved_$Stamp"
    }

    if ($Execute) {
        Move-Item -Path $Source -Destination $Destination
    }

    Write-Host "MOVE: $Source -> $Destination"
}

function Remove-ItemSafe($Path) {
    if (-not (Test-Path $Path)) {
        return
    }

    if ($Execute) {
        Remove-Item -Path $Path -Recurse -Force
    }

    Write-Host "REMOVE: $Path"
}

Write-Host ""
Write-Host "CardVector Tools Folder Cleanup"
Write-Host "Mode:" ($(if ($Execute) { "EXECUTE" } else { "DRY RUN" }))
Write-Host ""

if (-not (Test-Path $Tools)) {
    Write-Host "Tools folder not found at: $Tools"
    exit 1
}

# Keep these project tools in Tools/
$Keep = @(
    "cleanup_cardvector_docs.ps1",
    "validate_production_startup.py"
)

# Move LosslessCut / Electron app runtime outside the repository
$LosslessItems = @(
    "__pycache__",
    "locales",
    "Lossless Cut",
    "resources",
    "chrome_100_percent.pak",
    "chrome_200_percent.pak",
    "d3dcompiler_47.dll",
    "dxcompiler.dll",
    "dxil.dll",
    "ffmpeg.dll",
    "icudtl.dat",
    "libEGL.dll",
    "libGLESv2.dll",
    "LICENSE.electron.txt",
    "LICENSES.chromium.html",
    "LosslessCut.exe",
    "resources.pak",
    "snapshot_blob.bin",
    "v8_context_snapshot.bin",
    "vk_swiftshader.dll",
    "vk_swiftshader_icd.json",
    "vulkan-1.dll"
)

Ensure-Dir $LosslessDest

foreach ($Item in $LosslessItems) {
    Move-ItemSafe (Join-Path $Tools $Item) $LosslessDest
}

# Create a simple Tools README if missing
$ToolsReadme = Join-Path $Tools "README.md"
if (-not (Test-Path $ToolsReadme)) {
    $Text = @"
# Tools

This folder contains CardVector project utilities only.

Third-party applications and portable software should not be stored here.

Current utilities:

- cleanup_cardvector_docs.ps1
- validate_production_startup.py
"@
    if ($Execute) {
        $Text | Set-Content -Path $ToolsReadme -Encoding UTF8
    }
    Write-Host "CREATE FILE: $ToolsReadme"
}

Write-Host ""
Write-Host "Cleanup complete."
Write-Host ""
Write-Host "Next checks:"
Write-Host "  Get-ChildItem Tools"
Write-Host "  Get-ChildItem $LosslessDest"
Write-Host "  git status"
Write-Host ""
Write-Host "To actually move files, rerun with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\Tools\cleanup_tools_folder.ps1 -Execute"
