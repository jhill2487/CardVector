# Phase 8 Validation

## Focused Pricing

- Phase 3, Phase 7, and Phase 8 Marketplace Intelligence discovery:
  62 passed.
- Historical Marketplace Intelligence and Price Vector suite: 21 passed.
- Phase 8 focused suite: 15 passed.
- Application-layer suite: 6 passed.
- Listing Optimizer acceptance test: passed with the business-aware `$1.77`
  floor and configured free-shipping policy.
- Marketplace Intelligence smoke test: passed.
- Python compilation for all changed modules, `putnam_os.py`, and `main.py`:
  passed.

Phase 8 coverage includes canonical profile loading and saving, packaging
totals, eBay one/two/three-ounce postage, eBay and TCGplayer fees, acquisition
overrides, configurable free-shipping and margin thresholds, minimum viable
price, no-market review behavior, application delegation, new/existing
inventory parity, CSV reporting, and temporary-SQLite persistence.

## Protected Regression Suites

- Batch workflow: 11 passed.
- CardUploader inventory: 12 passed.
- Capture: 12 passed.
- Mobile queue: 25 passed.
- Supabase and storefront contracts: 26 passed.
- Workflow context: 3 passed.
- Desktop workflow contracts: 5 passed.
- Mobile thumbnail pairs: 3 passed.
- Architecture checker unit tests: 12 passed.
- Capture Studio, Auto Capture, OBS, Orders, and eBay policy smoke tests:
  passed.

## Static And Safety Checks

- Architecture checker warning and strict modes: 48 documented baseline
  findings, zero new findings.
- Production launcher SHA-256 remained
  `AD5044D8D439CE6B321951E85A335DE86927AAA9453FE05DF0A23C1327006EE7`
  and still targets `putnam_os.py`.
- Architecture Markdown links: passed.
- Manifest and Business Profile JSON validation: passed.
- Bundled Node `--check Docs/app.js`: passed.
- Phase 8 secret-pattern scan: passed.
- `git diff --check`: passed.

## Pre-Existing Non-Blocking Failures

- `Tools.test_mobile_location_contract`: 13 of 14 passed. The one stale
  assertion still searches `Docs/app.js` for the pre-photo-mode
  `captureRoute(...)` source string documented in Phase 7.
- `test_inventory_audit_mode_v1_0.py`: the existing OneDrive
  `test_artifacts/inventory_audit_v1_0/audit_images` permission error
  reproduced before test execution. Phase 8 does not change that test or
  subsystem.

The previously stale Listing Optimizer expectations were directly affected by
Phase 8 and were updated to the approved business-aware floor and shipping
policy; the acceptance test now passes.

No validation made a live marketplace call, modified production inventory,
wrote a production database, or changed Capture.
