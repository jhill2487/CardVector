# CardVector putnam_os.py Decomposition Plan

**Status:** Proposed
**Current file:** `Platform/Putnam_OS/System/app/putnam_os.py`
**Risk:** High
**Strategy:** Incremental extraction with forwarding interfaces; no rewrite

## Evidence Summary

The file currently contains:

- repository import-path bootstrap,
- configuration and policy persistence,
- CSV and money helpers,
- pricing/export preparation,
- performance and activity logging,
- pending-work discovery and workflow actions,
- capture sessions, thumbnail pairing, OBS status, and auto-capture state,
- inventory conversion, ETB/location UI, labels, and QR resolution,
- CardUploader import and inventory snapshots,
- inventory audit state and reports,
- marketplace comparison matching and analytics,
- acquisition and work-session persistence,
- Orders UI,
- the `PutnamOS` Tkinter shell and all primary pages.

The production launcher targets this file, so it remains operational throughout decomposition.

## Decomposition Rules

1. Extract behavior before moving UI.
2. Add characterization tests before each extraction.
3. Keep old functions/methods as forwarding wrappers until callers migrate.
4. Do not change paths, schemas, formulas, and UI layout in the same extraction.
5. One responsibility group per commit.
6. The `PutnamOS` class remains the production shell until late in the roadmap.
7. New services return plain result models and domain errors, never message boxes.
8. The old module must never import compatibility code that imports it back.

## Extraction Map

| Current responsibility and evidence | Future owner/module | Required dependencies | Risk | Order | Validation |
|---|---|---|---|---|---|
| `_bootstrap_repo_import_path`, ROOT/SYSTEM path setup, `sys.path` mutation | `cardvector.bootstrap`; `infrastructure.filesystem.paths` | Package metadata, workspace settings | High | 2 | Start outside repo cwd; both workstations |
| `load_app_config`, `save_app_config` | `infrastructure.configuration.application_settings` | Atomic JSON repository, schema | Medium | 3 | Existing settings round-trip; missing/corrupt config |
| `money`, `decimal_money`, `format_decimal_money` | `shared.domain.money` | `Decimal` only | Medium | 4 | Boundary/rounding parity |
| `read_csv`, `write_csv`, `normalize_column_name`, `find_column(s)` | Owner-specific importers plus `infrastructure.serialization.csv` | Paths, encoding policy | Medium | 4 | Existing CSV fixtures and UTF-8/BOM |
| `run_decision_engine_check`, `decision_engine_summary_text`, `latest_decision_log` | Decision owner pending; likely `marketplace_intelligence.application` or application status/reporting | Decision port, report repository | High | Deferred | Current Marketplace UI behavior |
| eBay policy functions `load_ebay_business_policies` through `validate_ebay_business_policies` | `shipping.domain.policies` and configuration repository | Validated settings | High | 7 | Policy configuration test; no export column change |
| `optimized_export_price`, `calculate_market_value`, `apply_pricing_strategy` | `marketplace_intelligence` canonical API | Explicit FMV/pricing models | High | 5 | Pricing consolidation fixtures; formula absence |
| `prepare_listing_export_rows`, `summarize_final_prices`, `export_summary_text`, `validate_export_price_floor` | `listings.application.export_service` | Pricing result, shipping policies, eBay adapter | High | 7 | Exact eBay headers/rows and cancellation |
| `append_export_history`, `append_pricing_performance_log` | Listings/Marketplace report repositories | Logging/report path ports | Medium | 7 | Existing CSV columns and append behavior |
| `todays_jobs_count`, `latest_completed_job`, `latest_carduploader_export`, `current_workflow_stage`, `next_recommended_action` | `application.workflows.job_query_service` | Workflow repository, bounded folder index | Medium | 1 | Current Home pending-work tests |
| `latest_capture_session`, capture-session path helpers | `capture.application.session_query` | Capture repository | Medium | 6 | Existing folder association |
| `capture_pair_rows`, `capture_pair_status`, `capture_cards_completed` | `capture.domain.pairs` and Capture query service | Capture models | High | 6 | Front-only/front-back fixtures, incomplete pair |
| `build_capture_thumbnail_image`, path fallback/logging | Capture thumbnail service plus desktop renderer | Image adapter, filesystem port | Medium | 6 | Desktop/mobile thumbnail pair tests |
| `load_inventory_label_generator`, `ensure_label_dependencies`, `generate_inventory_label_pdf` | Inventory label application service; PDF renderer adapter | Inventory registry, report renderer | Medium | 9 | QR payload and PDF output parity |
| `load_auto_capture_settings`, signature/threshold helpers | Capture domain/application and configuration | Image signature adapter | High | 6 | Auto-capture stability/duplicate tests |
| ETB parsing and conversion functions `etb_parent_from_batch` through `inventory_conversion_dashboard_stats` | `inventory.domain.locations`, `inventory.application.conversion` | Inventory repository, Capture service port | High | 8 | Conversion session/resume/registry sync |
| CardUploader inventory functions `require_carduploader_inventory_columns` through `import_carduploader_inventory` | `integrations.carduploader.inventory_import` plus Inventory application service | CSV importer, Inventory repository | High | 8 | Existing inventory CSV fixtures |
| generic/CardUploader import functions `detect_type` through `normalize_inventory_rows` | `integrations.carduploader.csv_import` and owner importers | File/CSV ports | High | 7 | Detected format, row count, missing fields |
| inventory audit functions `latest_ebay_active_listings_report` through `generate_inventory_audit_reports` | `inventory.application.audit` and repositories | eBay import adapter, report renderer | High | 9 | Resume, actions, confirmed-only export |
| comp/matching functions `card_fields` through `market_analyze`, `audit_new_listing` | `marketplace_intelligence` evidence/matcher APIs | Provider data, explicit evidence models | High | 5 | Saved fixtures; active listings not FMV |
| acquisition functions `acquisition_record_path` through `write_acquisition_job_metadata` | `inventory.application.acquisitions` or future provenance owner | Acquisition repository | Medium | 10 | Existing JSON and optional acquisition behavior |
| work-session functions `current_session_path` through `latest_sessions` | `application.workflows.session_service` | Session repository | Medium | 10 | Start/end/resume/job attachment |
| `PutnamOS.build_styles`, widget helpers, tree helpers | `presentation.desktop` shared widgets/style | Tkinter only | Low/Medium | 11 | Visual/manual desktop check |
| Home/workflow methods `workflow_job_snapshot` through `workflow_job_row`, `home_page` | Application job queries plus `presentation.desktop.views.home` | Application services | Medium | 1/11 | Only three home sections, actions exact |
| Capture Queue methods | `capture.application.queue_service`; `views.capture_queue` | Background job runner, queue port | High | 6/11 | Atomic claim, retry, auto processing |
| Processing/import methods | application workflow plus `views.processing` | CardUploader import, MI, Listings | High | 7/11 | Import -> pricing -> export context |
| Capture page methods `capture_page` through `check_obs_status_ui` | Capture service plus `views.capture` | Capture API, OBS status port | High | 6/11 | Manual/auto/mobile capture unchanged |
| Marketplace methods | MI API plus `views.marketplace` | MI service | Medium | 5/11 | Standalone/integrated parity |
| Orders methods | Orders service plus `views.orders` | Orders API, filesystem/open-folder port | Medium | 9/11 | Grouping and pick-list output |
| Inventory conversion/registry/labels/audit methods | Inventory services plus `views.inventory` | Inventory API, Capture port | High | 8-9/11 | ETB hierarchy, conversion, labels, audit |
| Settings save/sync methods | Configuration commands plus `views.settings` | Config/location sync services | Medium | 3/11 | Secrets hidden; all settings persist |
| Pricing progress and report-view methods | `views.processing` and background job results | Application job service | Medium | 7/11 | Progress only while active |
| `browse`, `load`, `auto_run`, success/failure callbacks | Processing workflow command and desktop adapter | Import, MI, Listings, reports | High | 7/11 | Representative full CSV run |

## Recommended Extraction Sequence

### Step 0 - Characterization

Before extraction:

- compile current modules,
- run all current smoke tests,
- add a production-launch import test,
- capture representative input/output fixtures,
- record current manual workflow results,
- resolve or preserve current uncommitted Price Vector work.

### Step 1 - Workflow Query Boundary

Use `workflow_context.py` as the seed.

Extract:

- pending-work discovery,
- workflow job lookup and updates.

Keep:

- `home_page` widgets,
- `workflow_job_row` rendering,
- old top-level functions as wrappers.

Why first: bounded, already modular, high value, and no business formula change.

### Step 2 - Packaging And Bootstrap

Introduce the package entry and path service while still starting the existing `PutnamOS` class. Do not change UI behavior.

### Step 3 - Configuration And Logging Facades

Move loading/writing behind interfaces. Preserve existing files and keys. This enables later services to receive settings rather than import globals.

### Step 4 - Stable Shared Primitives

Extract only tested money/result/error primitives and technology-neutral serialization helpers. Do not create a broad utility dump.

### Step 5 - Marketplace Intelligence Delegation

Complete current consolidation:

- explicit FMV input,
- canonical pricing,
- comp/evidence matching,
- persistence.

Leave top-level wrappers in `putnam_os.py`.

### Step 6 - Capture

Promote existing `capture_studio.py` and `obs_connection_manager.py`, then move pair/thumbnail/auto-capture behavior. Preserve mobile queue claim and dated routing.

### Step 7 - Processing, Listings, And Shipping

Extract:

- import workflow,
- business policies,
- export row preparation,
- export logging,
- eBay handoff context.

The UI remains visually unchanged.

### Step 8 - Inventory Conversion And Registry

Promote `inventory_locations.py`, conversion sessions, and cloud sync behind Inventory APIs. Resolve the tool-to-app import direction.

### Step 9 - Inventory Audit, Labels, Orders, Reports

Move each as a separate package/commit. Preserve all generated formats and QR payloads.

### Step 10 - Acquisitions And General Work Sessions

Decide whether acquisitions remain active before extraction. Retain data even if UI remains deferred.

### Step 11 - Split Presentation Views

Only after callbacks delegate:

- move Home,
- Capture,
- Processing,
- Marketplace,
- Orders,
- Settings,
- contextual Inventory views.

The final shell owns navigation and composition, not business behavior.

### Step 12 - Thin Legacy Module

`putnam_os.py` becomes either:

- a compatibility import/launch wrapper, then is retired, or
- a presentation module with no domain/application logic until final package move.

## Compatibility Pattern

During extraction:

```python
def prepare_listing_export_rows(...):
    return _listing_export_service.prepare_rows(...)
```

The wrapper:

- preserves arguments and result,
- contains no fallback formula,
- is covered by delegation and parity tests,
- has a registered removal phase.

## Per-Step Acceptance Criteria

- no changed production output unless explicitly approved,
- old function/interface still passes existing tests,
- new service has unit tests,
- no new `sys.path` mutation,
- no UI imports below Presentation,
- no source/runtime path move in behavior extraction,
- manual smoke test completed,
- rollback is one commit revert,
- owner approves before the next extraction.

## Stop Conditions

Stop and reassess if:

- a fixture changes unexpectedly,
- current UI callers cannot be identified,
- a migration requires schema and logic changes together,
- a service starts importing Tkinter,
- a compatibility wrapper gains business logic,
- capture or inventory state cannot be restored,
- the working tree includes unrelated modifications.
