# Phase 4 Capture Inventory

All paths are relative to
`C:\Users\user\OneDrive\PutnamCollectibles`.

## Active Production Implementations

| Path | Responsibility and public surface | Callers and side effects | Phase 4 disposition |
| --- | --- | --- | --- |
| `Platform/Putnam_OS/System/app/capture_studio.py` | `CaptureStudioService`, `CaptureResult`, session naming, OBS screenshot acquisition, front/back file naming, retake, session JSON | Constructed by `putnam_os.py`; writes dated Capture folders and `capture_session.json`; moves retakes | Proven compatibility implementation behind canonical Capture service |
| `Platform/Putnam_OS/System/app/obs_connection_manager.py` | `OBSConnectionManager`, connection status, cached client, retry/reconnect, screenshot request | Used by Capture Studio; holds live OBS client only when invoked | Retain as OBS adapter; no behavior relocation in Phase 4 |
| `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` | Cloud queue listing/claiming, atomic staging, dated routing, front-only/front-back mapping, manifests, controlled complete/fail/retry, CLI | Imported by `putnam_os.py`; reads Supabase; downloads originals; writes staging, Capture, conversion metadata | Proven compatibility implementation behind canonical Capture service; CLI retained |
| `Platform/Putnam_OS/System/app/putnam_os.py` | Capture UI, queue polling, zero-touch scheduling, auto-capture state, pair/thumbnail metadata, CardUploader handoff | Directly constructs desktop/mobile services; Tkinter callbacks; opens folders/browser | UI remains; service construction and domain rules delegate through Application/Capture |
| `Docs/app.js` and mobile static assets | Authenticated mobile camera, crop, draft recovery, upload and capture-layout metadata | Browser/Supabase; public deployment | Contract only; unchanged |
| `supabase/migrations/20260713153000_mobile_capture.sql` | Private capture session/image tables, storage and RLS foundation | Supabase deployment | Contract evidence; unchanged |
| `supabase/migrations/20260713170000_mobile_capture_authenticated_grants.sql` | Authenticated grants/policies | Supabase deployment | Contract evidence; unchanged |
| `supabase/migrations/20260716090000_mobile_capture_type.sql` | `NEW_CAPTURE` and `PHYSICAL_INVENTORY` contract | Mobile and desktop queue | Contract evidence; unchanged |

## Standalone and Secondary Capture Implementations

| Path | Observed responsibility | Current status | Phase 4 disposition |
| --- | --- | --- | --- |
| `Platform/Putnam_Platform/capture/Putnam_Capture.py` | Standalone console OBS capture, own session format under Incoming Files, keyboard controls, preview, auto-capture | Has dedicated batch launcher; not called by production CardVector OS | Retain unchanged pending operator decision; register as secondary legacy candidate |
| `Platform/Putnam_Platform/capture/obs_capture_autocrop.py` | Offline OpenCV card-border crop, debug image and metadata output, optional watch mode | Dedicated launcher; not called by production CardVector OS | Retain as capture preprocessing utility; the identifier hook is a no-op |
| `Platform/Putnam_Platform/tools/Run_Putnam_Capture.bat` | Launches standalone `Putnam_Capture.py` | Secondary launcher | Retain; do not alter production launcher |
| `Platform/Putnam_Platform/tools/Run_OBS_AutoCrop.bat` | Launches offline crop tool | Secondary tool launcher | Retain unchanged |

## Capture Logic Currently Embedded in the Desktop Module

| Functions/methods | Responsibility | Planned delegation |
| --- | --- | --- |
| `capture_pair_rows`, `capture_pair_status`, `capture_cards_completed` | Pair metadata and completeness | Canonical `cardvector.capture.pairing`; legacy names forward |
| `normalize_auto_capture_settings`, `capture_frame_signature`, `signature_difference`, `auto_capture_thresholds` | Auto-capture rules and image-difference math | Canonical `cardvector.capture.auto_capture`; legacy names forward |
| `capture_queue_*` methods | UI scheduling and rendering around queue operations | Application-facing Capture service for operations; Tkinter scheduling remains |
| `start_capture_session_ui`, `capture_next_card_ui`, `perform_auto_capture`, retake/finish methods | UI orchestration | Resolve and call `CaptureApplication`; no widget extraction |
| thumbnail widget methods | Image rendering and selection UI | Presentation remains; pair metadata moves to Capture |
| inventory-conversion capture methods | Inventory workflow plus capture service use | Inventory behavior remains; only service creation may delegate |

## Tests and Fixtures

- `Platform/Putnam_OS/System/app/test_capture_studio_v1.py`
- `Platform/Putnam_OS/System/app/test_auto_capture_v2_1.py`
- `Platform/Putnam_OS/System/app/test_obs_connection_manager_v1.py`
- `Platform/Putnam_OS/System/app/test_mobile_capture_thumbnail_pairs.py`
- `Platform/Putnam_OS/System/tools/test_mobile_capture_queue.py`
- `Tools/test_mobile_capture_supabase_contract.py`
- `Tools/validate_mobile_capture_crop_math.js`

The existing suites cover session naming, exact filenames, front/back alternation,
retake movement, OBS authentication/reconnect behavior, atomic claim guards,
capture-type routing, mobile pair mapping, metadata files, queue actions,
thumbnail pair completeness, RLS/static-site contracts, and crop math.

## Duplication Findings

1. Production Capture Studio and standalone Putnam Capture both acquire OBS
   screenshots but use different paths, session formats, and operator surfaces.
   They are not safe to merge in this phase.
2. Auto-capture rules exist in `putnam_os.py` while standalone Putnam Capture
   has separate historical auto-capture behavior. Production CardVector rules
   are canonical for the desktop application.
3. Pair/status metadata is capture-domain logic embedded in the Tkinter module.
4. Mobile queue infrastructure is correctly outside UI, but its service is
   constructed and called directly by the UI rather than the Application layer.
5. Numerous versioned backup modules remain beside production source. They are
   baseline violations and are not changed in Phase 4.
