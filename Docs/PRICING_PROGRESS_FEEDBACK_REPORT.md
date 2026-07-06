# Pricing Progress Feedback Report

Timestamp: 2026-06-29 09:15:00 -04:00

## Summary

Added visible progress feedback to the Putnam OS CardUploader pricing/export
workflow.

This was a low-risk UX and observability change. Pricing rules, export logic,
shipping policy logic, generated CSV columns, and business data were not
changed.

## Files Modified

- `Platform/Putnam_OS/System/app/putnam_os.py`

## Files Created

- `Docs/PRICING_PROGRESS_FEEDBACK_REPORT.md`

## Progress UI Added

The Pricing page now includes a progress panel with:

- current stage
- row count progress when rows are being priced
- elapsed time
- determinate progress bar
- final completion state

The active stages are:

- Loading CSV
- Validating rows
- Confirming shipping policy
- Applying pricing rules
- Counting cart sweeteners
- Confirming final export
- Writing eBay CSV
- Writing export log
- Checking market opportunities
- Complete

The existing confirmation popups remain in place.

## Telemetry Added

Completed pricing/export runs append timing telemetry to:

`Data/Logs/pricing_performance_log.csv`

Logged fields:

- timestamp
- input filename
- row count
- total runtime seconds
- load time seconds
- pricing time seconds
- export write time seconds
- output folder

The implementation uses `Platform/putnam_paths.py` through the existing
`DATA_LOGS_DIR` path.

Telemetry logging is best-effort. If the performance log cannot be written,
the export workflow should still complete normally.

## Busy State Cleanup

The UI now clears the pricing running state through `finally` after:

- successful completion
- user cancellation
- handled error

Cancellation and handled errors also update the visible progress panel.

## Encoding Issue Status

The workflow/checkmark/button strings are correct in the source file as:

- `✓`
- `→`
- `▶`

The previous `âœ“`-style issue appears fixed in the edited source. Some terminal
search output may still render Unicode poorly depending on console encoding.

## Tests Run

```text
py -m py_compile Platform\Putnam_OS\System\app\putnam_os.py Platform\Putnam_OS\System\app\main.py Platform\Putnam_OS\System\app\bulk_price_engine.py Platform\Putnam_OS\System\app\run_pricing_cli.py
```

Result: passed.

```text
py -c "... audit_new_listing(... dry_run=True, progress_callback=...) ..."
```

Result: passed against
`Platform/Putnam_OS/System/app/test_artifacts/listing_optimizer_v1_2/sample_acceptance.csv`.

Dry-run result:

- rows: 8
- optimized price changes: 7
- cart sweeteners: 3
- progress callback stages reached through final export confirmation

## Known Issues

- A full manual UI test is still recommended because the app is Tkinter-based
  and the visual progress bar cannot be fully verified through `py_compile`.
- The dry-run intentionally stops before writing export files, so the telemetry
  CSV is verified by compile/static path review rather than a live export write
  during this safe test pass.
