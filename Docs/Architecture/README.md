# CardVector Architecture

## Purpose

This directory is the navigation and governance center for CardVector
architecture. It defines how new work is owned, reviewed, implemented, tested,
and migrated without creating parallel systems.

## Authority And Conflict Resolution

Use this order when guidance conflicts:

1. Product vision and permanent business governance
2. `CardVector_Architecture_Manifest.md`
3. Accepted entries in `CardVector_Architecture_Decision_Log.md`
4. Normative operational standards listed below
5. Approved phase plans and checklists
6. Advisory target plans and open-question documents
7. Historical audit reports

The Architecture Manifest and accepted Architecture Decision Records are the
highest-priority architecture sources of truth. Facts in an audit remain
evidence; a recommendation in an audit is not a binding decision.

## Current State

- **Current phase:** Phase 4 - Capture and Card Recognition Consolidation
- **Current production launcher:** `Platform/Putnam_OS/Run CardVector OS Production.vbs`
- **Current Python target:** `Platform/Putnam_OS/System/app/putnam_os.py`
- **Proposed future entry point:** `py -m cardvector`
- **Proposed future package root:** `Platform/cardvector/`
- **Migration status:** `Platform/cardvector/application` is the canonical
  orchestration layer, `Platform/cardvector/marketplace_intelligence` is the
  canonical pricing API, and `Platform/cardvector/capture` is the canonical
  Capture API; CardUploader remains the external recognition owner
- **Phase 0:** Preserved with commits, a recovery branch, and patch/ZIP artifacts
- **Phase 4:** Capture ownership and the external CardUploader recognition
  boundary are authorized; bootstrap, paths, entry-point, UI, inventory,
  listings, orders, and shipping migrations are not authorized

## Canonical Owners

| Responsibility | Canonical owner |
| --- | --- |
| Production startup | Current launcher plus future bootstrap composition root |
| Desktop presentation | Future `cardvector.presentation.desktop` |
| Workflow orchestration | `Platform/cardvector/application` |
| Shared business types | Future `cardvector.shared.domain` |
| Capture | `Platform/cardvector/capture` |
| Inventory and locations | Future `cardvector.inventory` |
| FMV, Price Vector, pricing intelligence | `Platform/cardvector/marketplace_intelligence` |
| Listings and eBay export records | Future `cardvector.listings` |
| Orders and fulfillment | Future `cardvector.orders` |
| Shipping | Future `cardvector.shipping` |
| Configuration, paths, persistence, logging | Future `cardvector.infrastructure` |
| External services | Future `cardvector.integrations` |
| Temporary migration forwarding | Future `cardvector.compatibility` |
| Card recognition | CardUploader; CardVector only orchestrates the handoff |

The complete current-to-future mapping is in
`CardVector_Subsystem_Ownership_Matrix.md`.

## Normative Documents

- [Architecture Manifest](CardVector_Architecture_Manifest.md)
- [Architecture Decision Log](CardVector_Architecture_Decision_Log.md)
- [Layering And Dependency Rules](CardVector_Layering_and_Dependency_Rules.md)
- [Subsystem Ownership Matrix](CardVector_Subsystem_Ownership_Matrix.md)
- [Entry Point And Bootstrap Standard](CardVector_Entry_Point_and_Bootstrap_Standard.md)
- [Configuration, Path, And Runtime Standards](CardVector_Configuration_Path_and_Runtime_Standards.md)
- [Development Standards](CardVector_Development_Standards.md)
- [Architecture Guardrails](CardVector_Architecture_Guardrails.md)
- [Validation And Rollback Standards](CardVector_Validation_and_Rollback_Standards.md)
- [Future Change Process](CardVector_Future_Change_Process.md)
- [Machine-Readable Manifest](cardvector_architecture_manifest.json)

## Advisory Migration Documents

These documents guide future decisions but do not authorize a migration:

- [Target Repository Structure](CardVector_Target_Repository_Structure.md)
- [putnam_os.py Decomposition Plan](CardVector_putnam_os_Decomposition_Plan.md)
- [main.py Retirement Plan](CardVector_main_py_Retirement_Plan.md)
- [Compatibility Strategy](CardVector_Compatibility_Strategy.md)
- [Migration Roadmap](CardVector_Migration_Roadmap.md)
- [Open Architecture Questions](CardVector_Open_Architecture_Questions.md)

## Operational Templates And Registers

- [ADR Template](ADR_Template.md)
- [Deprecation Register](Deprecation_Register.md)
- [Compatibility Adapter Register](Compatibility_Adapter_Register.md)
- [New File Request Template](New_File_Request_Template.md)
- [Small Change Checklist](Small_Change_Checklist.md)
- [Subsystem Change Checklist](Subsystem_Change_Checklist.md)
- [Architecture Change Checklist](Architecture_Change_Checklist.md)

ADRs use the name `CV-ADR-NNN-short-title.md` when a decision needs a dedicated
record. The summary must also be entered in
`CardVector_Architecture_Decision_Log.md`. Only the project owner may mark an
ADR Accepted.

## Audit And Baseline Evidence

- [Architecture Audit](../Reports/Architecture_Audit.md)
- [Repository Inventory](../Reports/Repository_Inventory.md)
- [Entry Point Report](../Reports/Entry_Point_Report.md)
- [Duplicate Module Report](../Reports/Duplicate_Module_Report.md)
- [Dependency Map](../Reports/Dependency_Map.md)
- [Module Ownership](../Reports/Module_Ownership.md)
- [Dead Code Report](../Reports/Dead_Code_Report.md)
- [Architecture Roadmap Audit](../Reports/Architecture_Roadmap.md)
- [Phase 0 Baseline](Phase_0_Baseline/)
- [Phase 1 Standards](Phase_1_Standards/)
- [Phase 1.5 Baseline Remediation](Phase_1_5_Baseline_Remediation/)
- [Phase 2 Application Layer](Phase_2_Application/)
- [Price Vector Integration Gate](Price_Vector_Integration_Gate/)
- [Phase 3 Marketplace Intelligence](Phase_3_Marketplace_Intelligence/)
- [Phase 4 Capture and Recognition](Phase_4_Capture_and_Recognition/)

## Change Approval

1. Classify the change with the small, subsystem, or architecture checklist.
2. Confirm the canonical owner and search for an existing implementation.
3. Write an ADR for changes to ownership, layers, entry points, package roots,
   runtime boundaries, or public subsystem contracts.
4. Obtain project-owner approval before implementing an architecture change.
5. Update the manifest, decision log, ownership matrix, and registers only when
   the approved decision changes them.

## Architecture Commands

From the repository root:

```powershell
py Tools\architecture\check_architecture.py
py Tools\architecture\check_architecture.py --strict
py -m unittest discover -s Tools\architecture -p "test_*.py"
```

Default mode reports findings and exits successfully unless the checker itself
cannot run. Strict mode fails for findings that are not in the approved baseline.
The checker never changes files.
