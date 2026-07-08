# CardVector Platform v1.1.0 Migration Summary

Timestamp: 2026-07-01

## Purpose

CardVector Platform v1.1.0 moves Capture Studio and inventory labeling closer to
daily production use without changing the locked platform architecture.

## Workflow Simplifications

- Capture Studio now centers on one production action: `Capture Next Card`.
- Manual front/back capture choices were removed from the Capture tab.
- Manual OBS launch/status controls were removed from the Capture tab.
- OBS connection state is passive and only shows `Retry` when disconnected.
- Capture review moved from a bottom filmstrip to a permanent right preview rail.
- Label generation moved into Inventory as Label Center instead of remaining only
  a standalone script.

## UX Improvements

- Operators no longer need to decide whether the next photo is front or back.
- Current session state focuses on session name, capture folder, cards captured,
  current card, and pair status.
- Recent capture pairs show front/back thumbnails, timestamp, pair number, and
  completion status.
- Inventory labels are generated as timestamped PDFs under `Data/Exports/Labels/`.

## Safety Boundaries

- CardVector Capture Studio still only captures images.
- CardUploader remains the recognition source.
- CardVector Pricing Engine was not modified.
- `PLATFORM_VISION.md` was not modified.
- Inventory Label Center reads location registries and writes label PDFs only.
- Inventory records and databases are not modified by label generation.

## Backup

Checkpoint backup created at:

```text
Platform/Putnam_OS/System_Archive/cardvector_platform_v1_1_0_20260701_165425
```

## Follow-Up Items

- Validate Capture Studio v2 against live OBS on the production workstation.
- Add future label templates for long boxes, binder spines, shelves, and card
  show cases.
- Add a true Developer Mode later if manual OBS diagnostics are needed in the UI.
