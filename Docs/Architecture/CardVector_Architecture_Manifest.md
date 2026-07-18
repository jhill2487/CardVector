# CardVector Architecture Manifest

**Status:** Proposed for owner approval
**Prepared:** 2026-07-17
**Scope:** Permanent architecture and migration policy
**Evidence baseline:** The eight completed reports in `Docs/Reports`

## Authority

After explicit owner approval, this package becomes the architectural source of truth for CardVector. Until approval, it is a design proposal and does not authorize implementation, file movement, or cleanup.

The evidence baseline is:

- `Docs/Reports/Architecture_Audit.md`
- `Docs/Reports/Repository_Inventory.md`
- `Docs/Reports/Entry_Point_Report.md`
- `Docs/Reports/Duplicate_Module_Report.md`
- `Docs/Reports/Dependency_Map.md`
- `Docs/Reports/Module_Ownership.md`
- `Docs/Reports/Dead_Code_Report.md`
- `Docs/Reports/Architecture_Roadmap.md`

When this manifest conflicts with a historical report, the report remains evidence and this manifest records the proposed future decision. Product vision and business governance remain higher-level authorities.

## Architectural Mission

CardVector is a workflow platform for trading card operations. It coordinates:

`Capture -> CardUploader -> Processing and Price Vector -> eBay handoff`

CardVector owns workflow orchestration, capture preparation, pricing intelligence, operational inventory, supported exports, and operator guidance. External products retain the responsibilities they actually perform.

## Permanent Architecture Decisions

### A1. One installable Python package

Permanent production imports live under:

`Platform/cardvector/`

The package name is lowercase `cardvector`. Repository folders may retain business-facing names, but Python imports use PEP 8 lowercase package names.

### A2. One official Python entry point

The permanent Python entry point is:

`python -m cardvector`

implemented by:

`Platform/cardvector/__main__.py`

It delegates immediately to a bootstrap function. It contains no workflow or business logic.

### A3. One official production launcher

The existing:

`Platform/Putnam_OS/Run CardVector OS Production.vbs`

remains the official launcher during migration and is the preferred permanent launcher path unless operator validation identifies a stronger requirement. Its eventual command is `py -m cardvector`.

Other launchers may remain temporarily as tested compatibility redirects. They are not independent entry points.

### A4. Layered dependencies with vertical subsystem ownership

Permanent layers are:

1. Presentation
2. Application
3. Domain
4. Infrastructure
5. Integration
6. Compatibility

Subsystems are vertical owners. Capture, Inventory, Marketplace Intelligence, Listings, Orders, Shipping, Reporting, Analytics, Content, and any future Scanner package each own their domain and application behavior.

### A5. Marketplace Intelligence owns pricing

`cardvector.marketplace_intelligence` is the permanent owner of:

- normalized market evidence,
- Fair Market Value,
- Price Vector,
- pricing recommendations,
- pricing decision persistence,
- marketplace price analysis.

No UI, Listing Optimizer, Seller Tool, or Putnam OS adapter may calculate a competing price.

### A6. Recognition remains external in the current product

CardUploader is the current recognition and managed-inventory integration. CardVector must not duplicate recognition. A future native `cardvector.scanner` package requires a separate architecture decision and cannot be created as incidental feature work.

### A7. UI is an adapter

Tkinter code is confined to `cardvector.presentation.desktop`. It may translate operator actions into application commands and render results. It may not contain pricing, inventory, capture, matching, persistence, or marketplace business rules.

### A8. Bootstrap performs composition

Only the bootstrap knows concrete infrastructure and integration implementations. Domain and application code depend on interfaces/ports, not Tkinter, files, databases, OBS, Supabase, eBay, or browser automation.

### A9. Compatibility is temporary

Legacy import paths, functions, launchers, and output shapes may be preserved only through `cardvector.compatibility` or thin forwarding modules at old paths. Every adapter has an owner, tests, a removal condition, and a target phase.

### A10. Source and runtime data are separate

Source code, versioned defaults, migrations, and fixtures are tracked. Captures, logs, caches, exports, session state, operator settings, databases, and secrets are runtime data and are not tracked unless explicitly approved as sanitized fixtures.

### A11. Git is the source backup

Production source folders contain no timestamped copies or names using `old`, `backup`, `copy`, `final`, `new`, or version suffixes. Git commits, branches, tags, and release checkpoints preserve history.

### A12. Architecture is enforceable

CI and local checks must detect forbidden dependencies, duplicate entry points, path mutation, absolute user paths, runtime files in Git, imports from Archive, and unapproved production packages.

## Canonical Package Owners

| Responsibility | Permanent owner |
|---|---|
| Startup and dependency composition | `cardvector.bootstrap` |
| Desktop shell and navigation | `cardvector.presentation.desktop` |
| Cross-subsystem workflow | `cardvector.application` |
| Common value objects and errors | `cardvector.shared.domain` |
| Capture | `cardvector.capture` |
| Inventory and locations | `cardvector.inventory` |
| Marketplace evidence, FMV, Price Vector | `cardvector.marketplace_intelligence` |
| Listings and eBay-ready listing records | `cardvector.listings` |
| Orders and pick lists | `cardvector.orders` |
| Shipping policy and fulfillment settings | `cardvector.shipping` |
| Cross-workflow report coordination | `cardvector.reporting` |
| Analytics and metric definitions | `cardvector.analytics` |
| Content workflow, if retained | `cardvector.content` |
| Native scanner, only if approved | `cardvector.scanner` |
| Configuration, paths, logging, persistence, jobs | `cardvector.infrastructure` |
| External protocols | `cardvector.integrations` |
| Temporary legacy surfaces | `cardvector.compatibility` |

## Dependency Rule

The default dependency direction is:

`Presentation -> Application -> Domain`

Concrete runtime dependencies point inward through interfaces:

`Infrastructure/Integrations -> Application ports and Domain models`

Bootstrap may import all layers solely to compose them.

Compatibility may import canonical public APIs. Canonical packages must never import compatibility code.

## Public API Standard

Each subsystem exposes a small API from its package root or explicit `api.py`. Callers must not import private implementation modules. A public API change requires:

- compatibility analysis,
- tests,
- changelog entry,
- migration note,
- deprecation period when existing callers are affected.

Underscore-prefixed symbols and `internal/` modules are not public.

## Migration Method

CardVector uses a strangler migration:

1. Characterize current behavior.
2. Create or identify a canonical service.
3. Delegate the old interface to that service.
4. Migrate callers.
5. Validate production behavior.
6. Deprecate the old interface.
7. Remove or archive only after all removal criteria pass.

No phase may combine a subsystem rewrite with launcher, path, and data migration.

## Definition Of Architecture Compliance

A change is compliant when:

- it extends the canonical owner,
- dependencies follow the allowed direction,
- no second implementation or entry point is introduced,
- no runtime state is tracked as source,
- tests prove behavior and boundary compliance,
- documentation and ownership remain accurate,
- rollback is documented.

## Package Documents

- `CardVector_Target_Repository_Structure.md`
- `CardVector_Layering_and_Dependency_Rules.md`
- `CardVector_Subsystem_Ownership_Matrix.md`
- `CardVector_Entry_Point_and_Bootstrap_Standard.md`
- `CardVector_putnam_os_Decomposition_Plan.md`
- `CardVector_main_py_Retirement_Plan.md`
- `CardVector_Compatibility_Strategy.md`
- `CardVector_Configuration_Path_and_Runtime_Standards.md`
- `CardVector_Development_Standards.md`
- `CardVector_Architecture_Guardrails.md`
- `CardVector_Migration_Roadmap.md`
- `CardVector_Validation_and_Rollback_Standards.md`
- `CardVector_Future_Change_Process.md`
- `CardVector_Open_Architecture_Questions.md`
- `CardVector_Architecture_Decision_Log.md`

## Approval And Change Control

Approval authority: project owner.

After approval:

- architecture changes require a decision-log entry,
- ownership changes require manifest and matrix updates,
- a new top-level package or entry point requires explicit approval,
- implementation follows the migration roadmap,
- no cleanup begins until Phase 0 baseline protection is complete.
