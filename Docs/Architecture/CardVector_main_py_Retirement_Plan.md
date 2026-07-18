# CardVector main.py Retirement Plan

**Status:** Proposed investigation and migration plan
**File:** `Platform/Putnam_OS/System/app/main.py`
**Current classification:** Overlapping application, not proven dead
**Deletion authorized:** No

## Known Evidence

1. The official production VBS and BAT launchers target `putnam_os.py`, not `main.py`.
2. `main.py` defines a separate `PutnamOS(tk.Tk)` application and `main()` entry.
3. It owns:
   - root/path discovery,
   - rules loading,
   - CSV sniffing,
   - existing-listing normalization,
   - exact ladder delegation,
   - eBay bulk revise output,
   - new-listing review,
   - job logging,
   - a second dashboard/pricing/settings UI.
4. `Platform/Marketplace_Intelligence/tests/test_pricing_engine_consolidation.py` imports it as `legacy_main` and tests:
   - `apply_existing_ladder`,
   - `review_new_listing_prices`,
   - canonical pricing delegation.
5. The current untracked `patch_cardvector_ebay_existing_listings.py` references and edits `main.py`.
6. Documentation identifies it as overlapping/legacy, but no operator usage audit has yet proven it unused.

## Unknowns To Verify

- Windows desktop/start-menu shortcuts.
- Scheduled tasks or external scripts.
- Home-PC and work-PC manual launch habits.
- Imports outside files visible in the current clone.
- Whether users rely on its separate existing-listings workflow.
- Whether generated file names/columns differ from the production UI.
- Whether any tests load it by filesystem path rather than import.
- Whether its rule/config paths contain unique production settings.

## Retirement Strategy

### Stage 1 - Caller Inventory

Search:

- Python imports and path loaders.
- BAT/VBS/CMD/PowerShell launchers.
- documentation and runbooks.
- Windows shortcuts and scheduled tasks on both workstations.
- CI workflows.
- patch/install scripts.
- tests and fixtures.

Deliverable:

`main.py` caller inventory with owner and purpose for every result.

No behavior changes.

### Stage 2 - Characterization

Create fixtures for:

- supported input formats,
- existing listing normalization,
- price ladder changes,
- unchanged/invalid rows,
- bulk revise CSV headers and actions,
- new-listing review,
- job folder and log output,
- error cases.

Run `main.py` functions against those fixtures and record outputs.

### Stage 3 - Canonical Service Mapping

Map:

| `main.py` behavior | Canonical target |
|---|---|
| `find_root`, `ensure_dirs` | Infrastructure paths/runtime setup |
| `load_rules`, `normalized_ladder` | Marketplace Intelligence config |
| `sniff_rows`, `detect_file`, `find_col` | Listings/eBay import adapter |
| `normalize_existing_records` | Listings normalization |
| `apply_existing_ladder` | Marketplace Intelligence Price Vector adapter |
| `write_existing_upload_csv` | Listings eBay export |
| `existing_price_revision` | Processing application workflow |
| `review_new_listing_prices` | Processing application workflow |
| `log_run` | Structured logging plus business report |
| `PutnamOS` class | No replacement GUI; use canonical desktop shell |

### Stage 4 - Delegate Non-UI Functions

Replace each implementation with a thin call to canonical services. Preserve:

- function name,
- arguments,
- return shape,
- output names and columns,
- exception behavior where callers rely on it.

No independent formula remains.

### Stage 5 - Migrate Tests And Callers

- New tests target canonical services.
- Keep a smaller adapter test proving old names delegate.
- Update patch/tool callers to canonical APIs or retire them through their own approved package.
- Confirm no launcher invokes the second GUI.

### Stage 6 - Deprecate GUI Entry

If no operator uses it:

- make `main()` forward to `python -m cardvector` behavior or show a controlled deprecation message and start the canonical app,
- do not maintain a second Tkinter tree,
- document the transition.

If operator usage is discovered:

- preserve the user workflow as an action/view in the canonical application before redirecting.

### Stage 7 - Deprecation Period

Minimum:

- two validated production releases,
- successful use on home and work PCs,
- one complete listing workflow through the canonical app,
- no unresolved caller references.

Warnings should be logged, not shown repeatedly to the operator.

### Stage 8 - Removal Decision

Removal requires explicit owner approval and all criteria below.

## Forwarding Wrapper Decision

Recommended:

- retain `main.py` temporarily as an import/launch forwarding wrapper after its logic migrates,
- keep only documented public compatibility functions,
- route GUI `main()` to the canonical entry,
- include a removal-phase comment and tests.

The wrapper must not load old rules, write files, or construct the old UI independently.

## Removal Criteria

All must pass:

- no production launcher targets it,
- no external shortcut/scheduled task targets it,
- no canonical tests import it,
- all compatibility tests can move to `cardvector.compatibility`,
- all unique input/output behavior exists in canonical services,
- fixture parity passes,
- no runtime config/data is owned exclusively by it,
- two releases complete without fallback,
- Git/reference search is clean except archive/history/docs,
- owner approves removal,
- rollback tag exists.

## Rollback

Before each stage:

- commit current state,
- preserve fixture outputs,
- do not move the file.

Rollback is a commit revert. Before final removal, tag the last release containing the wrapper.

## Required Validation

- `py_compile` for old and canonical modules,
- focused pricing delegation tests,
- existing-listing and new-listing fixture parity,
- exact eBay CSV header/row comparison,
- canonical desktop startup,
- direct old entry invocation during deprecation,
- home/work workstation checks,
- Git reference search.

## Decision Boundary

Known evidence supports calling `main.py` overlapping and likely legacy. It does not yet support deletion. Retirement begins only after Phase 0 baseline and caller inventory approval.
