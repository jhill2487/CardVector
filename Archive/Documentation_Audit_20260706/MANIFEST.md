# Phase 0 Audit Artifacts Archive Manifest

Archive created: 2026-07-06 01:11:15

Cleanup package: Phase 0 Cleanup Package 01 - Root Audit Artifacts

Purpose: archive old root-level audit scripts and generated audit report text
files superseded by the Phase 0 governance reports.

Rollback: move the files listed below from this archive folder back to the
repository root.

## Scope Verification

- All files listed below were root-level files before archival.
- All files were audit, inspection, or generated report artifacts.
- Reference check found no active launcher or app references before archival.
- Documentation references in Phase 0 reports were left intact.

## Files Moved

| File | Type |
|---|---|
| `cardvector_batch_folder_inspector.py` | Audit / inspection script |
| `CARDVECTOR_BATCH_FOLDER_REPORT.txt` | Generated audit report |
| `cardvector_config_reference_finder.py` | Audit / inspection script |
| `CARDVECTOR_CONFIG_REFERENCE_REPORT.txt` | Generated audit report |
| `cardvector_folder_inspector.py` | Audit / inspection script |
| `cardvector_production_module_auditor.py` | Audit / inspection script |
| `CARDVECTOR_PRODUCTION_MODULE_REPORT.txt` | Generated audit report |
| `cardvector_production_path_auditor.py` | Audit / inspection script |
| `cardvector_production_path_auditor_v2.py` | Audit / inspection script |
| `CARDVECTOR_PRODUCTION_PATH_REPORT.txt` | Generated audit report |
| `CARDVECTOR_PRODUCTION_PATH_REPORT_V2.txt` | Generated audit report |
| `cardvector_production_reference_auditor.py` | Audit / inspection script |
| `CARDVECTOR_PRODUCTION_REFERENCE_REPORT.txt` | Generated audit report |
| `cardvector_root_cleanup_auditor.py` | Audit / inspection script |
| `CARDVECTOR_ROOT_CLEANUP_REPORT.txt` | Generated audit report |
| `cardvector_workspace_auditor.py` | Audit / inspection script |
| `CARDVECTOR_WORKSPACE_AUDIT_REPORT.txt` | Generated audit report |
| `FOLDER_INSPECTION_Putnam_OS.txt` | Generated inspection report |

## Files Intentionally Not Moved

- `AGENTS.md`
- `.putnam_root`
- `PLATFORM_VISION.md`
- `ScreenRecording_06-30-2026 14-42-57_1.MP4`
- Any folder at the repository root
- Any file under `Platform/`, `Business/`, `Data/`, `Capture/`, or `Docs/`

