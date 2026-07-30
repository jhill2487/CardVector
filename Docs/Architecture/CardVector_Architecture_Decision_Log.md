# CardVector Architecture Decision Log

**Status:** Proposed decisions awaiting project-owner approval
**Format:** Architecture Decision Records (ADR)

## CV-ADR-001 - Use One Installable `cardvector` Package

- **Decision:** Permanent production Python source uses the `cardvector` namespace under `Platform/cardvector`.
- **Status:** Proposed.
- **Evidence:** Current imports require path mutation and multiple peer source roots.
- **Rationale:** One namespace enables stable imports, packaging, tests, and multiple presentation adapters.
- **Alternatives considered:** Continue peer folders under `Platform`; use a root-level `src` migration immediately.
- **Consequences:** Current paths require temporary forwarding; packaging metadata is required.
- **Migration impact:** Phases 2-11.
- **Approval status:** Pending project owner.

## CV-ADR-002 - Official Python Entry Is `python -m cardvector`

- **Decision:** `cardvector.__main__.main` is the only permanent Python application entry.
- **Status:** Proposed.
- **Evidence:** Current launcher targets `putnam_os.py`; `main.py` and MI provide overlapping entry surfaces.
- **Rationale:** One compositional entry prevents startup/config divergence.
- **Alternatives considered:** Permanent `Platform/main.py`; continue direct script execution.
- **Consequences:** Launchers and tests migrate through compatibility.
- **Migration impact:** Phases 2-3.
- **Approval status:** Pending project owner.

## CV-ADR-003 - Retain Existing CardVector Production Launcher Path

- **Decision:** Keep `Platform/Putnam_OS/Run CardVector OS Production.vbs` as operator-facing production launcher and eventually redirect it to `py -m cardvector`.
- **Status:** Proposed.
- **Evidence:** Audit identifies it as current official launcher.
- **Rationale:** Stable operator behavior with internal modernization.
- **Alternatives considered:** New root launcher; rename/move launcher now.
- **Consequences:** Putnam OS folder retains one launcher even after source moves; aliases require deprecation.
- **Migration impact:** Phase 3 and Phase 11.
- **Approval status:** Pending project owner.

## CV-ADR-004 - Use Layered Dependencies With Vertical Subsystem Owners

- **Decision:** Presentation, Application, Domain, Infrastructure, Integration, and Compatibility rules apply; business ownership remains vertical by subsystem.
- **Status:** Proposed.
- **Evidence:** Current UI/business mixing and split Capture/Inventory ownership.
- **Rationale:** Prevents UI cycles while keeping each responsibility discoverable.
- **Alternatives considered:** Pure horizontal-layer repository; current feature folders without layer contracts.
- **Consequences:** Ports/adapters and bootstrap composition become standard.
- **Migration impact:** All phases.
- **Approval status:** Pending project owner.

## CV-ADR-005 - Marketplace Intelligence Owns FMV And Price Vector

- **Decision:** Marketplace Intelligence is the only pricing calculation owner.
- **Status:** Proposed reaffirmation of audit finding.
- **Evidence:** Independent MI package and current consolidation tests; duplicate Putnam OS formulas identified.
- **Rationale:** One source of truth and reusable engine.
- **Alternatives considered:** Putnam OS pricing owner; shared generic pricing utility.
- **Consequences:** Putnam OS/optimizer interfaces become adapters.
- **Migration impact:** Phase 5.
- **Approval status:** Pending project owner.

## CV-ADR-006 - Listings Owns Marketplace-Ready Records, Not FMV

- **Decision:** Listings validates and exports listing records; it consumes MI pricing results.
- **Status:** Proposed.
- **Evidence:** Export/business-policy logic currently mixed with pricing in UI/bulk modules.
- **Rationale:** Separates market decision from external schema.
- **Alternatives considered:** MI owns all eBay export; Putnam OS UI owns export.
- **Consequences:** Listings and Shipping packages are introduced during consolidation.
- **Migration impact:** Phase 5.
- **Approval status:** Pending project owner.

## CV-ADR-007 - CardUploader Remains Recognition Owner

- **Decision:** CardVector does not implement recognition in the current architecture; CardUploader is an external integration.
- **Status:** Proposed reaffirmation of current product boundary.
- **Evidence:** Production docs and archived scanner status.
- **Rationale:** Avoid duplicate product capability and preserve workflow.
- **Alternatives considered:** Restore archived scanner; create new native recognizer.
- **Consequences:** Future Scanner requires a new approved ADR.
- **Migration impact:** Phase 6 and future work.
- **Approval status:** Pending project owner.

## CV-ADR-008 - Bootstrap Is The Only Composition Root

- **Decision:** Concrete repositories/integrations are constructed only in `cardvector.bootstrap`.
- **Status:** Proposed.
- **Evidence:** Current modules discover paths/config and construct dependencies independently.
- **Rationale:** Testability, stable dependency direction, centralized startup failure.
- **Alternatives considered:** service locator globals; module-level singletons.
- **Consequences:** Services receive dependencies explicitly.
- **Migration impact:** Phases 2-8.
- **Approval status:** Pending project owner.

## CV-ADR-009 - Separate Workspace And User Runtime From Source

- **Decision:** Source, business workspace, and local user runtime are distinct configured concepts.
- **Status:** Proposed.
- **Evidence:** Business/runtime files coexist with Git source and some remain tracked.
- **Rationale:** Data safety, packaging, and multi-workstation reliability.
- **Alternatives considered:** Require repository root as all-purpose runtime root.
- **Consequences:** Current physical folders may remain initially; path service abstracts them.
- **Migration impact:** Phases 2, 4, 7, 11.
- **Approval status:** Pending project owner.

## CV-ADR-010 - Use Temporary Registered Compatibility Adapters

- **Decision:** Preserve old interfaces through tested forwarding modules with removal conditions.
- **Status:** Proposed.
- **Evidence:** `main.py`, pricing modules, Seller Tools, and launchers have known callers.
- **Rationale:** Avoid risky flag-day migration and permanent duplication.
- **Alternatives considered:** immediate moves; keep duplicate implementations permanently.
- **Consequences:** Compatibility registry and deprecation phases required.
- **Migration impact:** Phases 2-11.
- **Approval status:** Pending project owner.

## CV-ADR-011 - Decompose putnam_os.py By Strangler Extraction

- **Decision:** Extract services incrementally and leave forwarding behavior until UI callbacks migrate.
- **Status:** Proposed.
- **Evidence:** Nearly 9,000-line production monolith with existing focused service seams.
- **Rationale:** Preserve validated workflow and limit blast radius.
- **Alternatives considered:** rewrite desktop app; split UI files first.
- **Consequences:** Decomposition spans multiple releases and requires characterization tests.
- **Migration impact:** Phases 4-9.
- **Approval status:** Pending project owner.

## CV-ADR-012 - Retire main.py Only After Full Caller Migration

- **Decision:** Treat `main.py` as compatibility/legacy, not dead; redirect before removal.
- **Status:** Proposed.
- **Evidence:** Not production launcher target, but tests and patch script use it.
- **Rationale:** Evidence does not support deletion.
- **Alternatives considered:** immediate archive; maintain second GUI indefinitely.
- **Consequences:** Caller inventory, parity fixtures, deprecation period.
- **Migration impact:** Phase 10 and Phase 11.
- **Approval status:** Pending project owner.

## CV-ADR-013 - External Systems Use Ports And Adapters

- **Decision:** CardUploader, eBay, TCGplayer, Supabase, and OBS live under Integration adapters implementing application ports.
- **Status:** Proposed.
- **Evidence:** Protocol and business logic currently mixed in queue/UI/provider modules.
- **Rationale:** Vendor independence, testing, and failure isolation.
- **Alternatives considered:** vendor clients called directly by UI/domain.
- **Consequences:** Adapter interfaces and fakes required.
- **Migration impact:** Phases 5-8.
- **Approval status:** Pending project owner.

## CV-ADR-014 - Runtime Files Are Not Source

- **Decision:** Captures, logs, caches, exports, databases, resume state, and operator config are ignored runtime data unless sanitized fixtures.
- **Status:** Proposed.
- **Evidence:** Audit found tracked operational files despite ignore intent.
- **Rationale:** Prevent data loss/merge conflicts and keep clean clones.
- **Alternatives considered:** Git-sync operational state.
- **Consequences:** File-by-file migration and backup required.
- **Migration impact:** Phase 11.
- **Approval status:** Pending project owner.

## CV-ADR-015 - Architecture Guardrails Roll Out Incrementally

- **Decision:** Observe known debt, block new debt, then enforce fully after migration.
- **Status:** Proposed.
- **Evidence:** Immediate strict enforcement would fail on known monolith/path/backup debt.
- **Rationale:** Prevents drift without forcing unrelated cleanup.
- **Alternatives considered:** documentation-only rules; immediate all-or-nothing enforcement.
- **Consequences:** Narrow baseline allowlist with owners/expiry.
- **Migration impact:** Phases 2-12.
- **Approval status:** Pending project owner.

## CV-ADR-016 - Public Website Remains A Separate Deployment Artifact

- **Decision:** Private repository site source is exported through the allowlisted tool to `CardVector-site`; desktop code/runtime data never enter public output.
- **Status:** Proposed reaffirmation of current deployment.
- **Evidence:** `.github/workflows/pages.yml` and `Tools/export_cardvector_site.py`.
- **Rationale:** Keeps private platform source private and public site static.
- **Alternatives considered:** publish private repository Docs directly; manually maintain duplicate site source.
- **Consequences:** Docs/public-source boundary remains a known exception pending CV-OQ-017.
- **Migration impact:** Guardrails and deployment only.
- **Approval status:** Pending project owner.

## Decision Status Definitions

- **Proposed:** Designed, not approved.
- **Accepted:** Explicitly approved and binding.
- **Superseded:** Replaced by a newer ADR.
- **Deferred:** Intentionally postponed.
- **Rejected:** Considered and not selected.

Only the project owner changes approval status to Accepted.

## CV-ADR-017 - Enforce Architecture Standards Before Migration

- **Decision:** Adopt the Architecture Manifest, ownership rules, development
  standards, contribution rules, and warning-mode architecture checker as the
  binding standards for new repository changes.
- **Status:** Accepted.
- **Evidence:** Phase 0 preserved the current repository state and the project
  owner explicitly authorized Phase 1 on 2026-07-18.
- **Rationale:** New work must stop adding architectural debt before production
  code is migrated.
- **Alternatives considered:** defer standards until after migration; immediately
  enforce all rules against known legacy debt.
- **Consequences:** Existing violations are baselined and reported. New violations
  are reviewable in strict mode. Target-state ADRs CV-ADR-001 through CV-ADR-016
  retain their recorded status until individually approved or superseded.
- **Migration impact:** Phase 1 only. No production code, launcher, or runtime
  behavior changes are authorized by this decision.
- **Approval status:** Approved by project owner through the Phase 1 authorization.

## CV-ADR-018 - Establish The Canonical Application Layer Before Bootstrap

- **Decision:** Create `Platform/cardvector/application` as CardVector's
  canonical workflow-orchestration layer. During migration it accepts existing
  implementations as injected delegates. `putnam_os.py` may compose this
  facade temporarily without changing the production launcher.
- **Status:** Accepted.
- **Evidence:** The owner explicitly authorized Phase 2 Application Layer
  Extraction on 2026-07-18. `workflow_context.py` is the existing focused seam,
  while `putnam_os.py` contains cache, coordination, and handoff call sites.
- **Rationale:** Establish orchestration ownership with a reversible strangler
  step before moving UI, business logic, infrastructure, or subsystem code.
- **Alternatives considered:** Begin the earlier packaging/bootstrap roadmap
  phase; move `workflow_context.py`; rewrite workflows; defer all extraction
  until subsystem migrations.
- **Consequences:** The application package provides execution context, service
  registration, command dispatch, progress, cancellation, events, and a
  workflow facade. Existing workflow algorithms and persistence stay in place.
  Bootstrap, paths, entry points, and remaining package roots stay proposed.
- **Migration impact:** Phase 2 only. Creates active adapter `CV-COMP-012`.
- **Approval status:** Approved by project owner through the Phase 2 authorization.

## CV-ADR-019 - Establish Canonical Marketplace Intelligence Ownership

- **Decision:** Adopt `Platform/cardvector/marketplace_intelligence` as the
  canonical public owner of FMV, Price Vector, pricing confidence, normalized
  market evidence, pricing persistence contracts, and marketplace-pricing
  adapters. Preserve proven algorithms at their historical path behind tested
  aliases during delegation-first migration.
- **Status:** Accepted.
- **Evidence:** The project owner explicitly authorized Phase 3 on 2026-07-18;
  the Price Vector Integration Gate established separate FMV, recommendation,
  and final-price contracts; Phase 3 characterization proves exact output
  equivalence.
- **Rationale:** New callers require one stable owner without risking a
  simultaneous physical relocation and algorithm rewrite.
- **Alternatives considered:** rename/move the historical package immediately;
  retain both paths as peer owners; rewrite pricing; leave pricing in the UI.
- **Consequences:** `putnam_os.py` calls injected application pricing and pure
  evidence services. Legacy paths remain registered compatibility adapters
  with removal criteria. New code may not import the historical pricing path.
- **Migration impact:** Phase 3 only. No launcher, UI, capture, inventory,
  listings, orders, shipping, or live marketplace behavior changes.
- **Approval status:** Approved by project owner through the Phase 3 authorization.

## CV-ADR-020 - Establish Capture Ownership And External Recognition Boundary

- **Decision:** Adopt `Platform/cardvector/capture` as the canonical Capture
  owner and `cardvector.application.CaptureApplication` as its orchestration
  facade. CardUploader remains the sole production recognition owner;
  `Platform/cardvector/integrations/carduploader` provides a descriptive
  handoff adapter without implementing recognition.
- **Status:** Accepted.
- **Evidence:** The project owner explicitly authorized Phase 4 on 2026-07-18.
  Production source uses Capture Studio, the mobile queue, and CardUploader's
  browser/CSV workflow. No production source imports archived OCR engines.
- **Rationale:** Capture and recognition need an explicit boundary without
  copying proven Capture code or promoting conflicting archived scanner
  experiments.
- **Alternatives considered:** Relocate Capture implementations immediately;
  copy CardUploader behavior into CardVector; activate an archived OCR engine;
  keep direct UI ownership.
- **Consequences:** Capture helpers and operations have canonical APIs while
  proven implementations remain tested delegates. The UI and standalone tools
  remain compatibility surfaces. Native recognition requires a separate ADR.
- **Migration impact:** Phase 4 only. No launcher, UI layout, Marketplace
  Intelligence, Inventory, Listings, Orders, Shipping, database, or live-device
  behavior changes.
- **Approval status:** Approved by project owner through the Phase 4 authorization.

## CV-ADR-021 - CardUploader Owns Managed Inventory

- **Decision:** CardUploader is the canonical owner of managed inventory.
  CardVector uses application and CardUploader integration contracts for views,
  pricing, reporting, and workflow coordination.
- **Status:** Accepted.
- **Evidence:** CardUploader exports contain inventory identity, SKU, quantity,
  status, card identity, and location references. CardVector contains snapshot,
  audit, reconciliation, and ETB projection code but no reservation, allocation,
  pick-confirmation, or authoritative inventory API.
- **Rationale:** A second CardVector inventory implementation would create
  conflicting quantities, locations, and fulfillment state.
- **Alternatives considered:** create `cardvector.inventory`; treat local ETB
  JSON/Supabase as authoritative managed inventory; defer ownership.
- **Consequences:** `Platform/cardvector/inventory` is not created. Existing
  local projections remain temporary adapters. Unsupported live CardUploader
  capabilities are reported explicitly.
- **Migration impact:** Phase 5 establishes read-only snapshot contracts and
  application delegation. Data migration and schema changes are excluded.
- **Approval status:** Approved by project owner through the Phase 5 authorization.

## CV-ADR-022 - CardVector Owns Batch Workflow Status Only

- **Decision:** CardVector owns batch-level physical-inventory-conversion and
  price-review workflow status. CardUploader continues to own card-level
  inventory and batch-to-card associations.
- **Status:** Accepted.
- **Evidence:** Existing `workflow_context.py` and `putnam_os.py` callbacks
  already expose Capture, CardUploader, CSV, and price-review milestones
  without requiring batch contents. Phase 5 established CardUploader ownership.
- **Rationale:** CardVector needs resumable workflow visibility, not a second
  inventory truth.
- **Alternatives considered:** store batch contents in CardVector; store
  CardVector status in CardUploader without a supported API; keep status only
  in Tkinter memory.
- **Consequences:** `Platform/cardvector/batch_workflow` persists only batch
  milestones, timestamps, notes, confirmations, and artifact references.
  Card-level fields are forbidden.
- **Migration impact:** Phase 6 adds an application facade and registers the
  existing dashboard context as temporary adapter `CV-COMP-017`.
- **Approval status:** Approved by the project owner through the Phase 6 authorization.
- **Full ADR:** `CV-ADR-022-batch-workflow-ownership.md`

## CV-ADR-023 - Canonical Business Profile And Business-Aware Pricing

- **Decision:** Extend the existing Marketplace Intelligence Business Profile
  as the single source of seller economics. Every canonical pricing
  recommendation passes through a Business Rules Engine after FMV and Price
  Vector.
- **Status:** Accepted.
- **Evidence:** Marketplace Intelligence already owns FMV and Price Vector;
  repository packaging and postage foundations exist; the other business
  profiles are partial or legacy.
- **Rationale:** Acquisition, packaging, shipping, marketplace fees, and profit
  policy must produce one explainable seller recommendation without creating a
  second pricing or configuration system.
- **Alternatives considered:** A separate Business Intelligence package; Putnam
  OS profile ownership; hard-coded costs; independently writable pricing and
  business profiles.
- **Consequences:** `business_profile.json` is canonical,
  `pricing_profile.json` is a read-only fallback, reports and pricing
  persistence gain additive profitability fields, and shipping values remain
  estimates rather than fulfillment execution.
- **Migration impact:** Phase 8 only. No launcher, inventory, Capture,
  recognition, batch, publication, or live marketplace behavior changes.
- **Approval status:** Approved by the project owner through Phase 8 authorization.
- **Full ADR:** `CV-ADR-023-business-profile-and-pricing-intelligence.md`

## CV-ADR-024 - Supabase Owns The Shared Capture And Location Registry

- **Decision:** Supabase is the canonical source for shared capture batches,
  ETBs/storage locations, capture images, and their relationships. ETBs are
  canonical storage-location rows; ETB slots are child location rows. CardUploader
  remains the managed-inventory owner.
- **Status:** Accepted; production schema apply and legacy import remain gated.
- **Evidence:** Desktop OS reads legacy JSON while mobile capture writes
  Supabase upload/session artifacts; mobile staged sessions do not reach the
  local registry projection.
- **Rationale:** CardVector.app and CardVector OS need one shared registry that
  does not depend on desktop-local JSON conversion status.
- **Alternatives considered:** keep JSON authoritative; create separate ETB and
  location authorities; move managed inventory to CardVector.
- **Consequences:** Local JSON becomes migration input, comparison source,
  fallback cache, export, and historical audit. Production apply requires review
  of schema, mapping, dry-run conflicts, backup path, rollback, and commands.
- **Migration impact:** Adds canonical Supabase migration, trusted desktop
  integration, mobile canonical writes, desktop canonical read fallback, and
  dry-run migration tooling.
- **Approval status:** Implementation authorized by the project owner through the
  Supabase registry migration task; production cutover pending explicit approval.
- **Full ADR:** `CV-ADR-024-supabase-capture-location-registry.md`

## CV-ADR-025 - CardVector.app Is The Primary Future Operator UI

- **Decision:** CardVector.app is the primary future operator UI. CardVector OS
  remains the current production launcher target and a compatibility/admin
  desktop surface during migration. Scanner/OBS workflows are legacy/retirement
  candidates for the current workflow.
- **Status:** Accepted.
- **Evidence:** The project owner confirmed on 2026-07-30 that Scanner/OBS
  workflows are obsolete. Supabase, CardUploader, eBay, and Marketplace
  Intelligence already define the shared source-of-truth boundaries needed for a
  web-first operator interface.
- **Rationale:** New workflows should be usable away from the workstation and
  should not deepen desktop-local state dependency.
- **Alternatives considered:** Keep CardVector OS as permanent primary UI;
  immediately rewrite the desktop app; delete Scanner/OBS code immediately;
  maintain independent desktop and web implementations indefinitely.
- **Consequences:** New workflow UX defaults to CardVector.app. Desktop code is
  preserved as compatibility/admin tooling until migrated or retired through a
  controlled phase.
- **Migration impact:** Updates presentation ownership and roadmap priority. No
  production launcher, runtime behavior, code removal, or production data change
  is authorized by this decision.
- **Approval status:** Approved by the project owner in conversation on
  2026-07-30.
- **Full ADR:** `CV-ADR-025-cardvector-app-primary-ui.md`
