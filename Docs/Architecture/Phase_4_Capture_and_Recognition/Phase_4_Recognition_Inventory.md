# Phase 4 Recognition Inventory

All paths are relative to
`C:\Users\user\OneDrive\PutnamCollectibles`.

## Production Finding

CardVector contains no active production card-recognition engine.

Evidence:

- `CardVector_Architecture_Manifest.md` states that CardUploader owns current
  recognition.
- `CardVector_Subsystem_Ownership_Matrix.md` says production does not import
  scanner/OCR source.
- Repository search found no production import from
  `Archive/Scanner_Development`.
- `mobile_capture_queue.py` records that CardUploader remains the recognition
  system.
- `putnam_os.py` labels recognition as a future CardUploader handoff and does
  not invoke OCR.
- `capture_studio.py` writes images and session metadata only.
- `obs_capture_autocrop.py::identify_card_from_crop` only prints that a hook is
  ready; it performs no identification.

The Phase 4 canonical recognition decision is therefore:

> External CardUploader remains the single production recognition owner.
> CardVector owns a typed handoff boundary, not recognition algorithms.

## Active Recognition-related Production Surfaces

| Path | Surface | Actual behavior | Disposition |
| --- | --- | --- | --- |
| `Platform/Putnam_OS/System/app/putnam_os.py` | `open_carduploader`, CardUploader CSV import, workflow status | Opens configured CardUploader URL and later imports its CSV output | Route handoff description through an application-facing adapter; preserve browser and CSV behavior |
| `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` | staged manifest/session metadata | Prepares images and identifies CardUploader as downstream recognition owner | Preserve exact fields |
| `Platform/Putnam_Platform/capture/obs_capture_autocrop.py` | `identify_card_from_crop` | No-op print hook | Do not promote or treat as recognition |
| `Platform/Marketplace_Intelligence` and canonical MI adapters | CardUploader sales/inventory data normalization | Pricing evidence and CSV normalization, not recognition | Remains Marketplace Intelligence |

## Archived Scanner Research

The following are non-production research implementations and are not imported:

| Path | Functions/classes observed | Dependencies and behavior | Reuse status |
| --- | --- | --- | --- |
| `Archive/Scanner_Development/scanner_core_region_ocr.py` | Multiple redefined `scan_image` functions, OCR variants, SQLite loading, strict/fallback matching | Pillow, OpenCV, pytesseract, SQLite, label JSON, debug artifacts; accumulated patch generations in one file | Not reusable safely in Phase 4; conflicting implementations and hard-coded assumptions |
| `Archive/Scanner_Development/putnam_scanner_v2_2_0_region_ocr.py` | `RegionOCR`, `MatchResult`, `match_region_ocr`, preprocessing and CSV result writer | pandas, OpenCV, pytesseract, SQLite/CSV lookup, labeled border regions | Research evidence only; no production caller |
| `Archive/Scanner_Development/card_intake_app_v2_1_2_resurrected.py` | `OCRResult`, `MatchResult`, image preprocessing, candidate scoring, workbook writes and file movement | OCR, OpenCV, pandas/openpyxl, SQLite/CSV/XLSX, machine-specific Tesseract path | Too coupled to archived intake workflow and file movement |
| `Archive/Scanner_Development/region_ocr_matcher_v0_2.py` | Region warping, OCR, card matching | OpenCV, OCR, SQLite and debug folders | Experimental versioned implementation |
| `Archive/Scanner_Development/scanner_server.py` | Upload server and `try_run_engine` | HTTP server and archived scanner file layout | Archived development server; not a production boundary |

`scanner_core_region_ocr.py` contains repeated `scan_image` definitions from
successive patches. That is direct evidence that no single archived function
can be declared canonical without a separate recognition project and benchmark
approval.

## Recognition Data and Persistence Evidence

Archived engines expect combinations of:

- SQLite lookup tables such as `pokemon_cards`, `cards`, or
  `Pokemon_Lookup_Database`;
- CSV/XLSX card lookup data;
- border-label JSON;
- source images and generated crop/debug directories;
- result CSV or plain console output.

These paths are not part of the production CardVector contract. Phase 4 does
not open or modify a production recognition database.

## Contract Scope for Phase 4

The application-facing contract records:

- provider: CardUploader;
- source capture folder;
- capture session ID when available;
- capture type and ETB/location metadata when available;
- configured provider URL;
- handoff status;
- timestamp.

It does not claim to return a recognized card, confidence, candidates, OCR
evidence, or diagnostics. Those remain external until CardUploader returns the
existing CSV consumed by Processing.
