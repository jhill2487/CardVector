# Putnam OS v3.4.0 Workflow Update Report

Timestamp: 2026-06-29T15:39:00

## Files Modified

- `Platform/Putnam_OS/System/app/putnam_os.py`
- `Platform/Putnam_OS/System/app/test_listing_optimizer_v1_2.py`
- `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py`
- `Data/Config/fulfillment_profiles.json`
- `Docs/FULFILLMENT_PROFILES.md`
- `Docs/PROJECT_STATUS.md`
- `Docs/CHANGELOG.md`
- `Docs/AGENTS.md`
- `Docs/PROJECT_MANUAL.md`
- `Platform/Putnam_OS/CHANGELOG.md`
- `Docs/PUTNAM_OS_V3_4_0_WORKFLOW_UPDATE_REPORT.md`

## Pricing Rule Changes

- Retired the legacy `$0.89` cart sweetener export floor.
- Updated active Putnam OS Listing Optimizer floor to `$0.99`.
- Updated the lowest pricing tier so market prices `<= $1.50` export at `$0.99`.
- Updated cart sweetener tagging/counting to treat final prices `<= $0.99` as cart sweeteners.
- Preserved higher tiers:
  - `$1.51-$2.99` exports at `$1.49`
  - `$3.00-$4.99` exports at `$2.99`
  - `$5.00+` keeps market-based pricing
- Preserved eBay export columns.
- Did not change shipping policy or promotion export logic.

## Progress Feedback Added

Progress feedback for the CardUploader / Listing Optimizer workflow was already present from the prior progress patch and remains active:

- Loading CSV
- Validating rows
- Applying pricing rules
- Counting cart sweeteners
- Confirming shipping policy
- Confirming final export
- Writing eBay CSV
- Writing export log
- Running comp search
- Complete

The UI clears the busy state through `finally` after success, handled cancellation, or handled error.

## Telemetry Added

Pricing performance telemetry writes to:

```text
Data/Logs/pricing_performance_log.csv
```

Fields now include:

- timestamp
- input_filename
- row_count
- total_runtime_seconds
- load_time_seconds
- pricing_time_seconds
- export_write_time_seconds
- output_folder
- status

Telemetry failures are caught and reported to activity logging without blocking exports.

## Fulfillment Profiles Created

Config:

```text
Data/Config/fulfillment_profiles.json
```

Documentation:

```text
Docs/FULFILLMENT_PROFILES.md
```

Profiles created:

- Standard Envelope
- Ground Advantage

Status: config foundation only. These profiles are not connected to live profit calculations yet.

## Backlog Items Added

Updated `Docs/PROJECT_STATUS.md` with:

- Inventory Audit v2 - Backlog / Scheduled
- Profit Dashboard - Backlog / Planned
- Bulk Sales Performance Report - Backlog / Planned
- Offer Analytics Dashboard - Backlog / Planned
- Promotion Performance Dashboard - Backlog / Planned
- Module Completeness Pass - Backlog / Future

## Tests Run

- `py -m py_compile` on modified Python files:
  - `Platform/Putnam_OS/System/app/putnam_os.py`
  - `Platform/Putnam_OS/System/app/test_listing_optimizer_v1_2.py`
  - `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py`
  - `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_2.py`
- `py Platform/putnam_paths.py`
- Safe Listing Optimizer dry-run using existing sample CSV:
  - rows: 8
  - optimized price changes: 7
  - cart sweeteners: 3
  - minimum final export price: `$0.99`
  - average final export price: `$2.12`

## Known Issues

- Historical completed jobs and cache files may still contain `$0.89` because they are past generated outputs and were intentionally not modified.
- Fulfillment profiles are not yet connected to live Profit per Envelope reporting.
- Profit, offer, promotion, and bulk-sales dashboards remain backlog items and were not built in this update.
- Manual UI testing is still recommended before the next production batch, although the dry-run pricing path passed.
