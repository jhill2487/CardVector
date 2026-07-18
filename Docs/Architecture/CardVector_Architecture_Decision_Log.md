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
