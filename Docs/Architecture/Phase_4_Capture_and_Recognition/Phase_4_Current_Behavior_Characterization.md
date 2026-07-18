# Phase 4 Current Behavior Characterization

## Baseline Commands

The following commands ran before production changes, using the bundled Python
runtime.

| Scope | Result |
| --- | --- |
| `test_capture_studio_v1.py` | Pass |
| `test_auto_capture_v2_1.py` | Pass |
| `test_obs_connection_manager_v1.py` | Pass |
| `python -m unittest Platform.Putnam_OS.System.tools.test_mobile_capture_queue` | 25 passed |
| `python -m unittest Platform.Putnam_OS.System.app.test_mobile_capture_thumbnail_pairs` | 3 passed |
| `python -m unittest Tools.test_mobile_capture_supabase_contract` | 19 passed |

## Characterized Capture Contracts

| Case | Baseline behavior |
| --- | --- |
| First desktop session | Uses `MM.DD.YY` |
| Additional desktop session | Uses `.1`, `.2`, and later suffixes |
| Desktop pair order | front, back, next card front, next card back |
| Desktop filename | Six-digit card number plus `_front` or `_back` |
| Retake | Moves last file into `_retakes`; does not delete |
| Legacy mobile layout | Defaults to `FRONT_ONLY` |
| Explicit mobile pair layout | Sequence 1/2 maps to card 1 front/back |
| New capture routing | `Capture/MM.DD.YY[.n]` |
| Physical inventory routing | `Capture/Physical_Inventory_Conversion/MM.DD.YY[.n]` |
| Cloud claim | PATCH is guarded by `status=eq.PENDING_CONVERSION` |
| Queue race | Losing claimant receives no staged work |
| Pair completeness | Front-only needs no back; front/back does |
| OBS client | Reused and retried once after request failure |
| Missing OBS password | Fails before contacting OBS |

## Recognition Characterization

There is no active CardVector recognition output to compare. The current
production contract is the external handoff:

1. Capture produces ordered images and metadata.
2. Operator opens CardUploader.
3. CardUploader performs recognition externally.
4. Operator imports the CardUploader CSV.

No production OCR module, candidate list, recognition confidence, or
recognition database was found. Consequently, Phase 4 equivalence for
recognition means preserving the CardUploader handoff and CSV intake contract,
not inventing in-repository recognition results.

## Excluded Live Checks

The following require later operator validation and were not run:

- live desktop OBS screenshot;
- live auto-capture;
- live mobile upload;
- CardUploader recognition;
- real user Capture-folder changes.
