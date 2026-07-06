[CmdletBinding()]
param(
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

function Resolve-PutnamRoot {
    if (-not [string]::IsNullOrWhiteSpace($env:USERENVIRONMENT)) {
        return [System.IO.Path]::GetFullPath($env:USERENVIRONMENT)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $env:USERPROFILE 'OneDrive\PutnamCollectibles'))
}

function New-CleanupReason {
    param(
        [System.IO.FileSystemInfo]$Item
    )

    $name = $Item.Name
    $lower = $name.ToLowerInvariant()
    $isDirectory = ($Item.PSIsContainer -eq $true)
    $extension = if ($isDirectory) { '' } else { $Item.Extension.ToLowerInvariant() }

    if ($ProtectedFolders -contains $name) {
        return $null
    }

    if ($CanonicalFolders -contains $name) {
        return $null
    }

    if (-not $isDirectory -and $extension -eq '.zip' -and ($lower -match 'release|putnam|platform|os|capture|installer|patch')) {
        return 'release zip'
    }

    if (-not $isDirectory -and $extension -eq '.ps1' -and ($lower -match 'patch|hotfix|temp|installer|install|setup|cleanup|audit')) {
        return 'patch/install PowerShell file'
    }

    if ($isDirectory -and ($lower -match 'installer|installers|setup|release|build|dist|extract|extracted|temp|tmp|patch|hotfix')) {
        return 'old installer/temp release folder'
    }

    if (-not $isDirectory -and $lower -match '^run[ _-]*putnam[ _-]*os.*\.(bat|cmd|ps1|lnk)$') {
        return 'duplicate Run Putnam OS launcher'
    }

    if ($isDirectory -and $lower -match '^run[ _-]*putnam[ _-]*os') {
        return 'duplicate Run Putnam OS folder'
    }

    if (-not $isDirectory -and $extension -in @('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tif', '.tiff') -and ($lower -match 'screenshot|screen shot|capture|image|img_|obs|vlcsnap')) {
        return 'screenshot/image'
    }

    if (-not $isDirectory -and $extension -eq '.csv') {
        return 'loose CSV'
    }

    if ($isDirectory -and $lower -match 'capture[_ -]?session|root[_ -]?cleanup|temporary|scratch') {
        return 'temp extraction/capture folder'
    }

    return $null
}

function Get-UniqueDestination {
    param(
        [string]$DestinationFolder,
        [string]$Name
    )

    $candidate = Join-Path $DestinationFolder $Name
    if (-not (Test-Path -LiteralPath $candidate)) {
        return $candidate
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($Name)
    $extension = [System.IO.Path]::GetExtension($Name)
    $counter = 1
    do {
        $candidate = Join-Path $DestinationFolder ("{0}_{1:00}{2}" -f $baseName, $counter, $extension)
        $counter += 1
    } while (Test-Path -LiteralPath $candidate)

    return $candidate
}

function Format-EntryLine {
    param(
        [System.IO.FileSystemInfo]$Item,
        [string]$Reason,
        [string]$Destination,
        [string]$Status
    )

    $kind = if ($Item.PSIsContainer) { 'folder' } else { 'file' }
    return "[{0}] {1} | {2} | {3} -> {4}" -f $Status, $kind, $Reason, $Item.FullName, $Destination
}

$Root = Resolve-PutnamRoot
$CanonicalFolders = @(
    'Putnam_OS',
    'Putnam_Platform',
    'Work Sessions',
    'Collectr',
    'Exports',
    'Imports',
    'Media',
    'Archive',
    'Docs'
)
$ProtectedFolders = @(
    'Putnam_OS',
    'Putnam_Platform',
    'Work Sessions',
    'Collectr'
)

if (-not (Test-Path -LiteralPath $Root)) {
    throw "Putnam root does not exist: $Root"
}

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$archiveRoot = Join-Path $Root 'Archive'
$cleanupFolder = Join-Path $archiveRoot "Root_Cleanup_$timestamp"
$reportPath = Join-Path $cleanupFolder 'cleanup_report.txt'
$mode = if ($Apply) { 'APPLY' } else { 'DRY RUN' }
$report = New-Object System.Collections.Generic.List[string]

Write-Host "Putnam root: $Root"
Write-Host "Mode: $mode"
Write-Host ""

$report.Add("Putnam Root Cleanup Audit")
$report.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$report.Add("Root: $Root")
$report.Add("Mode: $mode")
$report.Add("")

Write-Host "Checking canonical folders..."
$report.Add("Canonical folder check:")
foreach ($folder in $CanonicalFolders) {
    $path = Join-Path $Root $folder
    if (Test-Path -LiteralPath $path) {
        Write-Host "  OK: $folder"
        $report.Add("  OK: $folder")
        continue
    }

    if ($Apply) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "  CREATED: $folder"
        $report.Add("  CREATED: $folder")
    } else {
        Write-Host "  WOULD CREATE: $folder"
        $report.Add("  WOULD CREATE: $folder")
    }
}

if ($Apply) {
    New-Item -ItemType Directory -Path $cleanupFolder -Force | Out-Null
} else {
    New-Item -ItemType Directory -Path $cleanupFolder -Force | Out-Null
}

$report.Add("")
$report.Add("Protected folders never moved:")
foreach ($folder in $ProtectedFolders) {
    $report.Add("  $folder")
}
$report.Add("")

Write-Host ""
Write-Host "Scanning root clutter candidates..."
$report.Add("Root clutter candidates:")

$items = Get-ChildItem -LiteralPath $Root -Force | Sort-Object PSIsContainer, Name
$candidates = New-Object System.Collections.Generic.List[object]

foreach ($item in $items) {
    if ($item.FullName -eq $cleanupFolder -or $item.FullName.StartsWith($cleanupFolder + [System.IO.Path]::DirectorySeparatorChar)) {
        continue
    }

    $reason = New-CleanupReason -Item $item
    if (-not $reason) {
        continue
    }

    $destination = Get-UniqueDestination -DestinationFolder $cleanupFolder -Name $item.Name
    $candidates.Add([PSCustomObject]@{
        Item = $item
        Reason = $reason
        Destination = $destination
    })
}

if ($candidates.Count -eq 0) {
    Write-Host "  No clutter candidates found."
    $report.Add("  No clutter candidates found.")
} else {
    foreach ($candidate in $candidates) {
        $status = if ($Apply) { 'MOVED' } else { 'WOULD MOVE' }
        if ($Apply) {
            Move-Item -LiteralPath $candidate.Item.FullName -Destination $candidate.Destination
        }

        $line = Format-EntryLine -Item $candidate.Item -Reason $candidate.Reason -Destination $candidate.Destination -Status $status
        Write-Host "  $line"
        $report.Add("  $line")
    }
}

$report.Add("")
$report.Add("Summary:")
$report.Add("  Candidates: $($candidates.Count)")
$report.Add("  Files/folders deleted: 0")
$report.Add("  Cleanup folder: $cleanupFolder")

$report | Set-Content -Path $reportPath -Encoding UTF8

Write-Host ""
Write-Host "Cleanup report:"
Write-Host $reportPath

if (-not $Apply) {
    Write-Host ""
    Write-Host "Dry run only. Re-run with -Apply to move the listed candidates."
}
