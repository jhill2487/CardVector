# Phase 6 Test Results

## Passing Results

- Batch workflow: 11 passed.
- Application layer: 6 passed.
- CardUploader inventory: 12 passed.
- Canonical and characterization Marketplace Intelligence: 32 passed.
- FMV separation and pricing consolidation: 21 passed.
- Canonical and characterization Capture: 12 passed.
- Capture Studio, Auto Capture, and OBS smoke scripts: passed.
- Mobile queue, Supabase, mobile-location, and storefront group: 64 passed.
- Thumbnail-pair tests: 3 passed.
- Workflow-context tests: 3 passed.
- Desktop workflow, Orders, and eBay policy scripts: passed.
- Architecture guardrails: 12 passed.
- Python `compileall`, application-runtime import/composition, manifest JSON,
  Architecture README links, Node syntax, secret-token pattern scan,
  `git diff --check`, and launcher target/hash: passed.
- Architecture checker strict mode: 48 baseline findings, zero new findings.

## Pre-Existing Non-Blocking Failures

1. `Tools.test_mobile_location_contract` expects the stale literal
   `captureRoute(state.etbId, state.location, state.captureType)`. The current
   front-only/front-back route has already superseded that source string.
2. `test_listing_optimizer_v1_2.py` expects `changes == 7`; current canonical
   pricing characterization passes and this old expectation was documented
   before Phase 6.

Phase 6 does not touch either implementation.

`test_inventory_audit_mode_v1_0.py` was not run because earlier baselines
identified a OneDrive test-artifact permission/mutation risk. Phase 5
read-only inventory contracts passed instead.

No test uses a production batch record, database, CardUploader account, live
marketplace, camera, OBS instance, or user Capture folder.
