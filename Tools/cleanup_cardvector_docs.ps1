param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$Root = Get-Location
$Docs = Join-Path $Root "Docs"
$Archive = Join-Path $Root "Archive"
$Reference = Join-Path $Docs "Reference"

function Ensure-Dir($Path) {
    if (-not (Test-Path $Path)) {
        if ($Execute) { New-Item -ItemType Directory -Path $Path | Out-Null }
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

Write-Host ""
Write-Host "CardVector Documentation / Archive Cleanup"
Write-Host "Mode:" ($(if ($Execute) { "EXECUTE" } else { "DRY RUN" }))
Write-Host ""

# Required folders
Ensure-Dir $Archive
Ensure-Dir $Reference
Ensure-Dir (Join-Path $Archive "Documentation")
Ensure-Dir (Join-Path $Archive "Reports")
Ensure-Dir (Join-Path $Archive "Scanner_Development")
Ensure-Dir (Join-Path $Archive "Historical")

# Docs -> Reference
$DocsReferenceFiles = @(
    "AI_ENGINEERING_CONTEXT.md",
    "FULFILLMENT_PROFILES.md",
    "PATH_MANAGER.md"
)

foreach ($File in $DocsReferenceFiles) {
    Move-ItemSafe (Join-Path $Docs $File) $Reference
}

Move-ItemSafe (Join-Path $Docs "Putnam_Standards") $Reference

# Docs -> Archive/Documentation
$DocsArchiveFiles = @(
    "AGENTS.md",
    "CARDVECTOR_CONSTITUTION.md",
    "GOVERNANCE.md",
    "GOVERNANCE_OVERVIEW.md",
    "PUTNAM_MANIFESTO.md",
    "PROJECT_STATUS.md",
    "ROADMAP.md"
)

foreach ($File in $DocsArchiveFiles) {
    Move-ItemSafe (Join-Path $Docs $File) (Join-Path $Archive "Documentation")
}

# Docs -> Archive/Reports
$ReportFiles = @(
    "CARDVECTOR_PLATFORM_V1_1_0_MIGRATION_SUMMARY.md",
    "INVENTORY_AUDIT_PROGRESS_REPORT.md",
    "PATH_MANAGER_IMPLEMENTATION_REPORT.md",
    "PRICING_PROGRESS_FEEDBACK_REPORT.md",
    "PUTNAM_OS_V3_4_0_WORKFLOW_UPDATE_REPORT.md",
    "ROOT_REORGANIZATION_REPORT.md"
)

foreach ($File in $ReportFiles) {
    Move-ItemSafe (Join-Path $Docs $File) (Join-Path $Archive "Reports")
}

Move-ItemSafe (Join-Path $Docs "reports") (Join-Path $Archive "Reports")

# Archive root loose scanner development files -> Archive/Scanner_Development
$ScannerPatterns = @(
    "scanner_*",
    "template_*",
    "run_*",
    "install_*",
    "README_SCANNER*",
    "README_PUTNAM*",
    "README_STUDIO*",
    "README_V*",
    "border_trainer*",
    "detect_card_borders*",
    "card_intake_app*",
    "region_ocr*",
    "requirements.txt",
    "PATCH_RULES_README.txt",
    "scanner_config.json",
    "server_old.txt",
    "unlock_locked_files.py",
    "relock_project_files.py",
    "verify_project_locks.py"
)

foreach ($Pattern in $ScannerPatterns) {
    Get-ChildItem -Path $Archive -File -Filter $Pattern -ErrorAction SilentlyContinue | ForEach-Object {
        Move-ItemSafe $_.FullName (Join-Path $Archive "Scanner_Development")
    }
}

# Root cleanup folders -> Archive/Historical/Root_Cleanup_20260627
$RootCleanupDest = Join-Path (Join-Path $Archive "Historical") "Root_Cleanup_20260627"
Ensure-Dir $RootCleanupDest

Get-ChildItem -Path $Archive -Directory -Filter "Root_Cleanup_20260627_*" -ErrorAction SilentlyContinue | ForEach-Object {
    Move-ItemSafe $_.FullName $RootCleanupDest
}

# Zero-byte mystery file "1" -> Archive/Historical instead of deleting
$Mystery = Join-Path $Archive "1"
if (Test-Path $Mystery) {
    Move-ItemSafe $Mystery (Join-Path $Archive "Historical")
}

Write-Host ""
Write-Host "Cleanup complete."
Write-Host ""
Write-Host "Next checks:"
Write-Host "  git status"
Write-Host "  tree Docs /F"
Write-Host "  Get-ChildItem Archive"
Write-Host ""
Write-Host "To actually move files, rerun with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\Tools\cleanup_cardvector_docs.ps1 -Execute"
