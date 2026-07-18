# CardVector Migration Roadmap

**Status:** Proposed
**Rule:** Approval of this document does not approve all implementation phases. Each phase has its own gate.

## Global Constraints

- Preserve the production workflow.
- One migration responsibility per commit/package.
- No cleanup in feature/extraction commits.
- No file retirement before caller and compatibility accounting.
- No runtime data move with a source-code move.
- Every phase begins from an approved checkpoint.
- Every phase stops for explicit owner approval.

## Authorized Phase Sequence Note

On 2026-07-18 the project owner explicitly authorized a narrower Phase 2 named
**Application Layer Extraction**. That authorization controls the current phase
and establishes only `Platform/cardvector/application`. The packaging, paths,
and bootstrap foundation described below remains deferred and requires a new
explicit phase authorization. No entry point or launcher change is implied.

## Phase 0 - Baseline And Protection

**Objective:** Establish a clean, reproducible baseline without losing current work.

**Exact scope:**

- current Price Vector/FMVs/persistence changes,
- current eBay patch and backup artifacts,
- architecture audit/planning documents,
- current operator/business data changes,
- current test baseline.

**Files/packages involved:**

- modified Marketplace Intelligence and Putnam OS pricing files,
- `Docs/PriceVector`,
- untracked pricing repository/migrations/tests,
- untracked patch/`.bak` files,
- current config/runtime changes.

**Preconditions:** None.

**Permitted:**

- inspect, validate, separate, commit, or deliberately stash existing work,
- create baseline test evidence,
- create a tag/checkpoint.

**Forbidden:**

- architecture moves,
- source cleanup,
- runtime data deletion,
- combining business files with source commits.

**Tests required:**

- current focused pricing tests,
- Putnam OS smoke tests,
- mobile queue contracts,
- `py_compile`,
- `git diff --check`.

**Manual validation:**

- official launcher,
- Capture -> CardUploader -> pricing -> eBay export,
- inventory registry,
- orders/pick list as currently supported.

**Rollback:** Return to the baseline tag; restore any stashed operator state.

**Completion criteria:**

- working tree clean or every remaining file intentionally documented,
- local HEAD equals approved remote baseline,
- known failures recorded,
- no valid work stranded in `.bak` or patch script only.

**Dependencies:** None.
**Risk:** Critical because current uncommitted work is vulnerable.

## Phase 1 - Architecture Manifest And Standards

**Objective:** Approve permanent ownership, layers, terminology, and change controls.

**Exact scope:** This `Docs/Architecture` package and governance entry links.

**Files/packages involved:**

- all architecture planning documents,
- later, root `AGENTS.md`, `Docs/PROJECT_INDEX.md`, and canonical read order.

**Preconditions:** Phase 0 baseline.

**Permitted:**

- documentation review/corrections,
- decision-log approval statuses,
- governance cross-links.

**Forbidden:**

- production code changes,
- file moves,
- launcher changes.

**Tests required:**

- document/link/path validation,
- architecture package completeness.

**Manual validation:**

- owner can identify entry point and every subsystem owner,
- new-developer read order is coherent.

**Rollback:** Revert documentation commit.

**Completion criteria:**

- manifest explicitly approved,
- open blocking questions assigned,
- decision log updated,
- governance points to this package.

**Dependencies:** Phase 0.
**Risk:** Low.

## Phase 2 - Packaging, Paths, And Bootstrap Foundation

**Objective:** Create an installable `cardvector` package and path/bootstrap factories without switching production.

**Exact scope:**

- packaging metadata,
- package skeleton,
- path settings model,
- bootstrap factory that can invoke current `PutnamOS`.

**Files/packages involved:**

- future `pyproject.toml`,
- future `Platform/cardvector/__init__.py`,
- future `__main__.py`,
- future `bootstrap.py`,
- future infrastructure path module,
- current `Platform/putnam_paths.py` as adapter.

**Preconditions:**

- approved manifest,
- clean baseline,
- path behavior characterized.

**Permitted:**

- add package/bootstrap/path modules,
- add tests,
- add forwarding facade.

**Forbidden:**

- redirect production VBS,
- move business/runtime data,
- decompose UI,
- remove current path logic.

**Tests required:**

- package build/import,
- `py -m cardvector` test entry in non-GUI mode,
- start from another working directory,
- path precedence and invalid path tests,
- adapter parity.

**Manual validation:**

- package imports on home/work PCs,
- resolved paths match current production paths.

**Rollback:** Remove/revert new package commit; current launcher is unchanged.

**Completion criteria:**

- no new path requires `sys.path` mutation,
- current and new path objects agree,
- current app can be constructed by bootstrap in test mode.

**Dependencies:** Phases 0-1.
**Risk:** High.

## Phase 3 - Official Entry Point Consolidation

**Objective:** Switch the official launcher to the package entry without changing application behavior.

**Exact scope:** Production launcher target and startup logging/error boundary.

**Files/packages involved:**

- `Platform/Putnam_OS/Run CardVector OS Production.vbs`,
- `cardvector.__main__`,
- `cardvector.bootstrap`,
- startup validation tests.

**Preconditions:**

- Phase 2 passes on both workstations,
- old launcher target remains available.

**Permitted:**

- redirect the one official VBS,
- retain aliases as compatibility redirects,
- improve bootstrap-level error reporting.

**Forbidden:**

- change UI/workflows,
- retire `putnam_os.py`,
- change configuration schemas.

**Tests required:**

- official entry invocation,
- nonzero failure exit,
- missing optional integration behavior,
- clean shutdown.

**Manual validation:**

- official VBS on home/work PCs,
- all primary workspaces open,
- background workers start/stop.

**Rollback:** Point the VBS back to `putnam_os.py`.

**Completion criteria:**

- one launcher labeled production,
- production starts through `py -m cardvector`,
- prior target retained for one shadow release.

**Dependencies:** Phase 2.
**Risk:** High.

## Phase 4 - Shared Infrastructure Extraction

**Objective:** Centralize configuration, logging, filesystem, serialization, and job execution.

**Exact scope:** Separate packages/commits:

- 4A configuration,
- 4B logging,
- 4C filesystem/atomic writes,
- 4D background executor,
- 4E stable serialization primitives.

**Files/packages involved:**

- current helpers in `putnam_os.py`, `main.py`, capture, orders, inventory, Seller Tools, and MI,
- future `cardvector.infrastructure`,
- future `cardvector.shared`.

**Preconditions:**

- package entry stable,
- characterization tests for each helper semantic.

**Permitted:**

- introduce ports/adapters,
- migrate one caller group at a time,
- preserve old facades.

**Forbidden:**

- broad utility rewrite,
- change runtime locations and behavior simultaneously,
- migrate business formulas into Shared.

**Tests required:**

- config precedence/atomic writes,
- path portability,
- log redaction,
- executor error/cancel/shutdown,
- CSV/JSON encoding parity.

**Manual validation:**

- settings persist,
- logs created and sanitized,
- UI remains responsive,
- both workstations.

**Rollback:** Revert the individual 4A-4E commit; facades retain prior behavior.

**Completion criteria:**

- new services receive injected settings/paths,
- no new direct root discovery,
- infrastructure has no Tkinter/business rules.

**Dependencies:** Phase 3.
**Risk:** Medium/High.

## Phase 5 - Marketplace Intelligence, Listings, And Shipping Consolidation

**Objective:** Establish one market/pricing owner and separate listing/export/policy responsibilities.

**Exact scope:**

- finish current Price Vector delegation,
- move remaining evidence/matching behavior,
- define Listings export service,
- define Shipping policy service,
- preserve eBay CSV and UI interfaces.

**Files/packages involved:**

- `Platform/Marketplace_Intelligence`,
- `System/MarketIntelligence/Pricing`,
- `bulk_price_engine.py`,
- pricing/export/policy functions in `putnam_os.py` and `main.py`,
- Listing Optimizer/Seller Tools compatibility paths,
- future MI/Listings/Shipping packages.

**Preconditions:**

- current Price Vector work committed,
- representative fixtures,
- external eBay schema captured.

**Permitted:**

- adapters and delegation,
- typed FMV/recommendation/final models,
- listing and policy services,
- persistence migration already approved for Price Vector.

**Forbidden:**

- new pricing strategy,
- live provider expansion,
- recognition/Grade Vector,
- eBay upload automation,
- CSV column changes.

**Tests required:**

- all focused MI/Price Vector tests,
- delegation/formula-absence tests,
- eBay output parity,
- shipping policy tests,
- legacy adapter tests.

**Manual validation:**

- sample CardUploader import,
- pricing review,
- export summary,
- open export/eBay handoff.

**Rollback:** Revert each delegation commit; preserve migration backup and compatibility path.

**Completion criteria:**

- one pricing implementation,
- UI contains no FMV/strategy formula,
- Listings owns output records,
- Shipping owns policy semantics.

**Dependencies:** Phase 4.
**Risk:** Critical.

## Phase 6 - Capture Consolidation And Scanner Boundary

**Objective:** Canonicalize Capture while reaffirming CardUploader recognition ownership.

**Exact scope:**

- Capture Studio,
- OBS manager,
- mobile queue,
- front-only/front-back models,
- thumbnails,
- dated routing,
- capture settings/manifests,
- legacy capture caller inventory.

**Files/packages involved:**

- `capture_studio.py`,
- `obs_connection_manager.py`,
- `mobile_capture_queue.py`,
- Capture functions/UI methods in `putnam_os.py`,
- `Platform/Putnam_Platform/capture`,
- Supabase capture migrations,
- future Capture and integration packages.

**Preconditions:**

- path/config infrastructure stable,
- complete Capture characterization,
- operator decision on standalone legacy tools.

**Permitted:**

- extract domain/service/adapter behavior,
- keep UI and CLI wrappers,
- preserve routing and cloud contracts.

**Forbidden:**

- OCR/recognition,
- capture redesign,
- Supabase schema weakening,
- archive legacy capture yet.

**Tests required:**

- Capture Studio tests,
- OBS manager tests,
- mobile queue/atomic claim tests,
- photo-mode/pair/thumbnail tests,
- routing tests,
- public Supabase contract.

**Manual validation:**

- desktop manual and auto capture,
- mobile front-only and front-back,
- disconnect/reconnect,
- exact local folders/thumbnails.

**Rollback:** Revert adapter/extraction commit; existing modules remain wrappers or intact.

**Completion criteria:**

- Capture package owns all capture rules,
- OBS/Supabase are adapters,
- mobile queue no longer imports app UI area,
- Scanner remains external/deferred by documented decision.

**Dependencies:** Phase 4.
**Risk:** Critical.

## Phase 7 - Inventory And Persistence Consolidation

**Objective:** Give operational inventory state, location identity, conversion, and persistence clear owners without changing data.

**Exact scope:** Separate migration packages:

- 7A Inventory locations/conversion/sync,
- 7B Inventory audit/reconciliation/labels,
- 7C persistence ports/repositories and old-state readers.

**Files/packages involved:**

- `inventory_locations.py`,
- inventory functions/UI in `putnam_os.py`,
- `inventory_reconciliation.py`,
- `generate_etb_qr_labels.py`,
- Seller Tools location registry,
- local JSON and Supabase location contracts,
- future Inventory and Infrastructure persistence packages.

**Preconditions:**

- runtime data classified/backed up,
- location authority decision approved,
- fixtures and conversion-resume tests.

**Permitted:**

- repository ports,
- service extraction,
- UI/CLI adapters,
- read compatibility for old state.

**Forbidden:**

- silent data rewrite,
- location/QR format change,
- inventory reassignment,
- CardUploader managed-inventory duplication,
- automatic shipping purchase.

**Tests required:**

- registry counts/status,
- cloud sync/idempotency,
- conversion start/resume/complete,
- audit actions/reports,
- labels/QR payload,
- old-state reads.

**Manual validation:**

- ETB hierarchy,
- physical conversion,
- label generation,
- inventory audit.

**Rollback:** Restore state backup and revert one subpackage commit.

**Completion criteria:**

- Inventory owns identity/occupancy/conversion,
- UI does not write state directly,
- old formats remain readable.

**Dependencies:** Phases 4 and 6 for Capture/Inventory boundary.
**Risk:** Critical.

## Phase 8 - Orders And Reporting Consolidation

**Objective:** Give fulfillment preparation and report rendering clear owners without changing order or output behavior.

**Exact scope:** Two independently approved packages:

- 8A Orders import/grouping/pick lists,
- 8B shared report rendering contracts and output catalog.

**Files/packages involved:**

- `orders_fulfillment.py`,
- Orders callbacks in `putnam_os.py`,
- subsystem report writers,
- future Orders and Reporting packages.

**Preconditions:**

- shared filesystem/config/log infrastructure stable,
- sample eBay orders fixtures,
- exact pick-list/report outputs captured.

**Permitted:**

- extract order models/services,
- preserve UI and CLI wrappers,
- introduce generic renderers without moving report meaning.

**Forbidden:**

- shipping-label purchase,
- inventory mutation,
- CardUploader fulfillment duplication,
- report schema changes,
- analytics feature expansion.

**Tests required:**

- order format detection,
- order/line grouping,
- quantity/SKU/location/shipping fields,
- pick-list output parity,
- report renderer encoding/path tests.

**Manual validation:**

- import representative order CSV,
- inspect grouped orders,
- generate/open printable pick lists,
- verify existing report folders.

**Rollback:** Revert 8A or 8B independently; existing module/writers remain available.

**Completion criteria:**

- Orders owns fulfillment preparation,
- report semantics remain with subsystems,
- generic rendering does not contain business decisions,
- existing output paths and formats remain compatible.

**Dependencies:** Phase 4; Inventory integration only through approved public IDs.
**Risk:** High.

## Phase 9 - putnam_os.py Application And Presentation Decomposition

**Objective:** Reduce the monolith after business services are canonical.

**Exact scope:**

- application workflow commands/queries,
- view modules,
- shell/navigation,
- UI adapters,
- remaining acquisition/session decision.

**Files/packages involved:**

- `putnam_os.py`,
- `workflow_context.py`,
- future `cardvector.application`,
- future desktop presentation package.

**Preconditions:**

- Phases 4-7 service APIs stable,
- method extraction map updated,
- UI characterization/manual checklist complete.

**Permitted:**

- move thin views/callbacks,
- delegate all behavior,
- preserve `PutnamOS` interface temporarily.

**Forbidden:**

- UI redesign,
- new workflows,
- business rule changes,
- main.py retirement in same commit.

**Tests required:**

- application command/query tests,
- UI model/source tests,
- all subsystem suites,
- production smoke.

**Manual validation:**

- every workspace/action,
- minimum window size,
- background thread shutdown,
- error paths.

**Rollback:** Revert one extracted view/application commit; old wrappers remain.

**Completion criteria:**

- Presentation contains only UI,
- application orchestration has no Tkinter,
- `putnam_os.py` is a thin shell/wrapper.

**Dependencies:** Phases 4-7.
**Risk:** Critical.

## Phase 10 - main.py Compatibility Migration

**Objective:** Retire the second GUI safely without deleting it prematurely.

**Exact scope:** Follow `CardVector_main_py_Retirement_Plan.md`.

**Files/packages involved:**

- `main.py`,
- pricing consolidation tests,
- patch/tool callers,
- launcher/shortcut evidence,
- Compatibility registry.

**Preconditions:**

- caller inventory complete,
- all unique behavior canonical,
- two-app output parity.

**Permitted:**

- forwarding functions,
- entry redirect,
- deprecation logs,
- migrate tests.

**Forbidden:**

- delete `main.py`,
- remove behavior without replacement,
- add features to legacy GUI.

**Tests required:**

- old import delegation,
- existing/new listing parity,
- direct old entry redirect,
- no duplicate formula.

**Manual validation:**

- work/home shortcuts,
- any discovered legacy workflow,
- canonical replacement.

**Rollback:** Revert wrapper/redirect commit.

**Completion criteria:**

- no live caller uses second GUI,
- wrapper only,
- deprecation period begins.

**Dependencies:** Phases 5 and 8.
**Risk:** High.

## Phase 11 - Legacy Archive, Runtime Tracking, And Cleanup

**Objective:** Remove proven ambiguity in small reversible packages.

**Exact scope:** One commit each:

- backup modules,
- `.bak`/patch artifacts,
- broken launchers,
- legacy capture after approval,
- superseded pricing modules after adapter removal,
- old launcher aliases,
- tracked runtime files,
- stale docs/empty folders after decisions.

**Files/packages involved:** Items in `Dead_Code_Report.md` and tracked-runtime inventory.

**Preconditions:**

- removal criteria for each item,
- reference and workstation search,
- backup/manifest,
- deprecation period complete.

**Permitted:**

- archive/move approved source,
- untrack runtime files without deleting local state,
- update references/docs.

**Forbidden:**

- mixed cleanup package,
- business data deletion,
- guessing,
- feature changes.

**Tests required:** Full affected subsystem and production smoke after every package.

**Manual validation:** Launchers, shortcuts, runtime state, operator data.

**Rollback:** Move back from archive or revert commit; restore data index/backup.

**Completion criteria:** No production ambiguity and manifest for every archived group.

**Dependencies:** Relevant earlier phases and deprecation periods.
**Risk:** Medium/High.

## Phase 12 - Automated Guardrails Enforcement

**Objective:** Convert architecture rules from documentation into CI protection.

**Exact scope:** Guardrail script/config, baseline allowlist, CI/pre-commit integration.

**Files/packages involved:**

- future architecture check tool,
- `pyproject.toml`,
- `.github/workflows`,
- import-linter contracts,
- tests/architecture,
- `.gitignore` after runtime migration.

**Preconditions:** Package boundaries and baseline debt known.

**Permitted:** Observe -> protect baseline -> enforce rollout.

**Forbidden:** Broad auto-fixing or guardrails that mutate source.

**Tests required:** Self-tests proving known good/bad fixtures.

**Manual validation:** Clear developer output and waiver process.

**Rollback:** Disable individual CI rule/config, not architecture package.

**Completion criteria:** New duplicate entry/path/layer/runtime violations fail CI.

**Dependencies:** Begins in Phase 2; full enforcement after Phase 11.
**Risk:** Medium.

## Phase 13 - Final Production Verification

**Objective:** Certify the permanent architecture and remove remaining transitional approvals.

**Exact scope:** Entire repository, application, package, deployment, docs, data policy.

**Files/packages involved:** All production packages, launchers, tests, docs, migrations.

**Preconditions:** Phases 0-12 complete.

**Permitted:** Defect fixes in separate commits; final docs/status updates.

**Forbidden:** New features or opportunistic refactors.

**Tests required:**

- full suite,
- package build/install,
- import graph/cycle checks,
- architecture guardrails,
- public export/secret scan,
- fresh workspace/database tests.

**Manual validation:**

- full workflow on home and work PCs,
- official launcher,
- Capture/CardUploader/Processing/eBay,
- Inventory and Orders,
- rollback drill,
- clean close.

**Rollback:** Return to last certified phase tag.

**Completion criteria:**

- one entry point,
- one owner per subsystem,
- no prohibited dependencies,
- no tracked runtime debt without approved exception,
- documentation matches behavior,
- owner signs off.

**Dependencies:** All prior phases.
**Risk:** High validation scope, low change scope.

## Phase Gate Template

Before each phase:

```text
Phase:
Baseline commit:
Scope:
Known unrelated changes:
Tests before:
Manual evidence before:
Rollback:
Owner approval:
```

After each phase:

```text
Commit(s):
Files changed:
Tests after:
Manual evidence after:
Differences:
Guardrails:
Rollback verified:
Owner approval to continue:
```
