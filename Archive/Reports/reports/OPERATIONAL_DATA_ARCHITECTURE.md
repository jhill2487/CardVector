# Operational Data Architecture

Generated: 2026-07-07

Scope: Phase 2 - Sprint 2.6.1A investigation only. This report does not move
data, change code, restore files, stash files, or implement migration.

## Summary

CardVector source code now syncs successfully through GitHub, but several live
business/session files are still stored inside the source repository. Opening or
running CardVector OS on the Work PC modified tracked JSON files under
`Platform/Putnam_OS/System/data/`, which confirms that Git is currently exposed
to live operational state.

The most important finding is that CardVector needs a shared operational data
root outside the source repository. Git should continue to version source code,
governance, documentation, configuration templates/defaults, and schemas. Live
inventory state, acquisition state, work-session state, conversion sessions,
capture outputs, labels, logs, and caches should live in a shared data root that
both Home PC and Work PC can access without committing runtime data.

## Current Dirty Files

The normal clean-working-tree precondition was waived for these files only.
They were inspected but not restored, stashed, committed, or pushed.

| File | Classification | Why it changed |
|---|---|---|
| `Platform/Putnam_OS/System/data/acquisitions/current_acquisition.json` | Runtime/session state | CardVector selected acquisition `ACQ-20260701_083129` and updated `selected_at` to `2026-07-07T08:05:19`. |
| `Platform/Putnam_OS/System/data/acquisitions/records/ACQ-20260701_083129.json` | Operational business data | The acquisition record stores purchase metadata, status, break-even fields, imports, pricing jobs, and attached work sessions. It was updated when the current acquisition/session was attached or refreshed. |
| `Platform/Putnam_OS/System/data/current_session.json` | Runtime/session state with operational context | The active work session stores current batch location, acquisition snapshot, pricing jobs, notes, and absolute local folder paths. |

These files include workstation-specific absolute paths such as
`C:\Users\user\OneDrive\PutnamCollectibles\...` and
`C:\Users\JaredHill\OneDrive\PutnamCollectibles\...`, which makes them unsafe
as Git-tracked shared state.

## Current Storage Map

| Data | Current location | Classification | Notes |
|---|---|---|---|
| Source code | `Platform/Putnam_OS/System/app/`, `Platform/Putnam_OS/System/tools/`, `Platform/putnam_paths.py` | Source code | Should remain tracked in Git. |
| Governance/docs | `Docs/`, root governance files | Source/governance | Should remain tracked in Git. |
| ETB registry | `Data/Config/etb_location_registry.json` | Operational business data / business configuration | Stores ETB IDs, A-J locations, capacities, active location, occupancy counts, QR payloads, and status. It is currently in a Git-trackable config area but behaves like live inventory state. |
| ETB occupancy | `Data/Config/etb_location_registry.json` | Operational business data | `stored_count`, `remaining_capacity`, `active_location`, and location status should not depend on Git. |
| Active location | `Data/Config/etb_location_registry.json` | Operational business data | Current active ETB location is live workflow state, not source configuration. |
| Batch/game location registry | `Platform/Putnam_OS/System/config/location_registry.json` | Operational business data / local config | Used by Seller Tools location suggestions and batch assignment. It contains operational location history and should be reviewed for migration. |
| Acquisition records | `Platform/Putnam_OS/System/data/acquisitions/records/*.json` | Operational business data | Contains purchase price, source, notes, attached sessions, imports, pricing-job references, and break-even fields. |
| Current acquisition pointer | `Platform/Putnam_OS/System/data/acquisitions/current_acquisition.json` | Runtime/session state | Workstation/session pointer that should be shared only if both workstations need to resume the same active workflow. |
| Current work session | `Platform/Putnam_OS/System/data/current_session.json` | Runtime/session state | Contains current active session and absolute local paths. Should move to shared operational runtime with portable path references. |
| Work session folders | `Work_Sessions/` | Operational business data / runtime session records | Contains session notes and session metadata. Should move or mirror into shared operational data. |
| Physical Inventory Conversion session JSON | `Platform/Putnam_OS/System/data/inventory_conversion/` | Operational business data / runtime session state | Contains `current_inventory_conversion.json` and `sessions/*.json`. These are currently ignored for new files but live inside the source repo. |
| Physical Inventory Conversion capture images | `Capture/Physical_Inventory_Conversion/<location>/<date>/` | Operational business data / generated capture output | Contains front-only conversion images and `capture_session.json`; currently includes absolute Home PC paths. |
| Capture session metadata/images | `Capture/<date>/capture_session.json` and JPG files | Runtime/session state / generated capture output | Capture Studio production output. Should not be committed. Large images should stay out of Git. |
| QR label outputs | `Data/Exports/Labels/` | Generated output | PDF/PNG labels are generated artifacts. They are already ignored by `.gitignore`. |
| Imports/exports | `Data/Imports/`, `Data/Exports/`, `Platform/Putnam_OS/Incoming Files/`, `Platform/Putnam_OS/Completed Jobs/` | Operational/generated data | Source CSV copies and generated job outputs are business-relevant but should not be source-controlled. |
| Logs | `Data/Logs/`, `Platform/Putnam_OS/System/logs/` | Runtime/generated files | Should remain ignored. |
| Cache | `Platform/Putnam_OS/System/cache/` | Cache/generated files | Should remain ignored and local or rebuildable. |
| App config | `Platform/Putnam_OS/System/config/*.json` | Mixed | Static defaults such as branding/pricing rules can remain tracked; machine-local or mutable operational config should be split out. |

## Why The Work PC Files Changed

The active code writes live state directly under the repository:

- `CURRENT_ACQUISITION_PATH = ACQUISITIONS_DIR / "current_acquisition.json"`
- `ACQUISITIONS_DIR = DATA / "acquisitions"`
- `current_session_path()` returns `DATA / "current_session.json"`
- Physical Inventory Conversion writes session JSON to
  `Platform/Putnam_OS/System/data/inventory_conversion/`.
- Physical Inventory Conversion writes capture data to
  `Capture/Physical_Inventory_Conversion/`.

When CardVector OS opens, selects the current acquisition, attaches the current
session, refreshes import metadata, or resumes conversion state, those JSON
files are rewritten with current timestamps and path values. Because some of
those files are tracked, Git reports them as modified even though the operator
only used the application.

## Proposed Shared Operational Data Root

Use a portable operational root outside the Git repository. The preferred
strategy should extend the existing `USERENVIRONMENT` path convention:

```text
%USERENVIRONMENT%\CardVector_Data
```

If `USERENVIRONMENT` is not set, the resolver should use the platform path
manager to choose a safe default near the repository's parent:

```text
<repo parent>\CardVector_Data
```

For the current OneDrive-based workstations, this would resolve to a shared
OneDrive folder beside the source repo, not inside it:

```text
C:\Users\<user>\OneDrive\CardVector_Data
```

This keeps source code and live operational state conceptually separate while
still allowing OneDrive to synchronize operational files between Home PC and
Work PC.

## Proposed Folder Structure

```text
CardVector_Data/
    Inventory/
        ETBs/
        Locations/
        InventoryRecords/
        Registries/
    ConversionSessions/
        Sessions/
        Captures/
    CaptureSessions/
    AcquisitionLots/
        Records/
        Runtime/
    WorkSessions/
    RecognitionJobs/
    Labels/
    Imports/
    Exports/
    Runtime/
    Logs/
    Cache/
```

## Migration Recommendations

Move or redirect first:

- `Platform/Putnam_OS/System/data/acquisitions/records/*.json`
- `Platform/Putnam_OS/System/data/acquisitions/current_acquisition.json`
- `Platform/Putnam_OS/System/data/current_session.json`
- `Platform/Putnam_OS/System/data/inventory_conversion/`
- `Capture/Physical_Inventory_Conversion/`
- `Work_Sessions/`
- `Data/Config/etb_location_registry.json`

Keep local/runtime-only:

- `Platform/Putnam_OS/System/cache/`
- `Platform/Putnam_OS/System/logs/`
- `Data/Logs/`
- temporary smoke-test outputs
- machine-specific config copies such as `*-DESKTOP-*.json`

Keep tracked in Git:

- source code
- governance and markdown documentation
- `.gitignore`
- configuration templates/defaults
- schema/default config examples
- static pricing/business rule defaults when they are not mutated by normal app use

Do not track:

- live acquisition records
- current acquisition/current session pointers
- ETB occupancy and active-location state
- conversion sessions
- capture images and capture metadata
- generated labels
- logs, caches, imports, exports, and completed jobs

## Git Hygiene Notes

The current `.gitignore` already ignores many generated paths, including:

- `/Capture/Physical_Inventory_Conversion/`
- `/Data/Exports/`
- `/Data/Logs/`
- `/Data/Processed/`
- `/Platform/Putnam_OS/System/cache/`
- `/Platform/Putnam_OS/System/logs/`
- `/Platform/Putnam_OS/System/data/inventory_conversion/`

However, ignore rules do not stop Git from tracking files that were already
committed. The three dirty files in this investigation are tracked and should be
removed from Git tracking only in a later migration commit, after their live
contents are safely copied or redirected to the shared operational data root.

## Safe Implementation Plan For Sprint 2.6.1

1. Add a shared operational data resolver to the platform path layer.
2. Add an operator-visible/default config for the operational data root.
3. Create shared operational folders if missing.
4. Redirect Physical Inventory Conversion session writes to
   `CardVector_Data/ConversionSessions/Sessions/`.
5. Redirect Physical Inventory Conversion captures to
   `CardVector_Data/ConversionSessions/Captures/`.
6. Read shared conversion sessions first, then fall back to existing local repo
   paths for backward compatibility.
7. Redirect acquisition/current-session state only after conversion workflow is
   stable on both workstations.
8. Remove tracked live-state files from Git tracking in a dedicated migration
   commit after data has been safely copied.

## Remaining Follow-Up Tasks

- Decide whether `Data/Config/etb_location_registry.json` should become a
  shared operational registry file or split into a tracked schema/default plus
  live `CardVector_Data/Inventory/Registries/etb_location_registry.json`.
- Decide whether current acquisition/current session pointers should be shared
  globally or workstation-specific under `Runtime/<workstation>/`.
- Normalize stored paths in session JSON to relative paths or stable IDs so
  Home PC and Work PC do not store each other's absolute usernames.
- Add migration tooling that copies, never moves, existing operational data into
  `CardVector_Data`.
- Add validation that Physical Inventory Conversion can resume ETB-001 Location
  A and B from the shared root.
- Add follow-up `.gitignore` rules only if new local fallback paths are created
  inside the repository.

