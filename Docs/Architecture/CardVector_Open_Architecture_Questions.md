# CardVector Open Architecture Questions

**Status:** Unresolved decisions
**Rule:** Do not invent answers when evidence is insufficient.

## Questions

| ID | Question | Why it matters | Current evidence | Evidence needed | Decision owner | Blocks | Temporary default |
|---|---|---|---|---|---|---|---|
| CV-OQ-001 | Is standalone Marketplace Intelligence a permanent supported application? | Determines whether its UI/CLI remain product entry surfaces | BAT, Python launcher, UI, CLI exist; Putnam OS also uses engine | Operator usage, distribution intent, support expectations | Project owner | MI package/entry cleanup | Keep it supported; do not retire |
| CV-OQ-002 | Is `System/app/main.py` launched outside Git-visible files? | Controls safe retirement | No production launcher targets it; tests and patch script use it | Desktop shortcuts, scheduled tasks, both workstation habits | Project owner | Phase 10 | Preserve and treat as compatibility |
| CV-OQ-003 | Are standalone legacy OBS capture tools still used? | Controls Capture archive timing | Current Capture Studio exists; legacy BAT/Python remain runnable | Operator confirmation and shortcut search | Project owner | Legacy Capture cleanup | Preserve |
| CV-OQ-004 | What is the permanent owner/purpose of `System/decision_engine`? | Avoids competing marketplace decision outputs | Partially active checks, placeholders, stale paths, Marketplace UI access | Current outputs, user value, desired scope | Project owner + architect | Decision Engine migration | Keep isolated; no expansion |
| CV-OQ-005 | Should Content remain a production subsystem? | Determines package and UI ownership | `content_page`, `Putnam_Content`, previous removal from Home | Current operational use and desired workflow | Project owner | Content package creation | Treat as business data/deferred |
| CV-OQ-006 | What is `Collectr` intended to contain? | Prevents unsafe cleanup or duplicate integration | No tracked implementation found | Operator history/purpose | Project owner | Root cleanup only | Leave untouched |
| CV-OQ-007 | Will CardVector ever own native scanner/recognition? | Determines whether `cardvector.scanner` is implemented | Scanner code archived; CardUploader is current source of truth | Product decision, business case, interface requirements | Project owner | Scanner implementation only | CardUploader remains owner |
| CV-OQ-008 | Is there one stable shared Card/Product identity model? | Crosses MI, listings, inventory, orders, CardUploader | Similar fields exist in CSV/provider logic | Field semantic audit, IDs, variants, conditions | Architect + subsystem owners | Shared card model | Keep adapter-local models |
| CV-OQ-009 | Should workspace data remain inside the Git worktree long term? | Affects packaging, multi-PC sync, and data safety | OneDrive repo currently contains Business/Data/Capture; Gitignore partial | Backup/sync requirements and operator preference | Project owner | Runtime-data separation | Keep location, separate logically/untrack |
| CV-OQ-010 | What is authoritative for location occupancy and status? | Prevents cloud/local conflict | Supabase owns cloud identity; local JSON is operational projection | Conflict-resolution and offline update tests | Inventory owner + project owner | Inventory consolidation | Preserve documented current split |
| CV-OQ-011 | Which tracked JSON/cache/config files are intentional shared state? | Needed before untracking | Several runtime files tracked despite ignore rules | File-by-file owner/authority/backup inventory | Project owner + architect | Phase 11 runtime cleanup | Do not untrack |
| CV-OQ-012 | Which database is permanent for pricing/inventory decisions? | Determines repository/migration implementation | Supabase capture/location; JSON state; active MI SQLite plan | Scale/offline/multi-PC requirements and migration tests | Project owner + architect | Persistence finalization | Use current stores behind ports |
| CV-OQ-013 | Should Putnam Seller Tools remain a named subsystem? | Affects SKU audit/location/listing tool ownership | Seller audit/planner useful; optimizer/location logic overlaps | Operator workflows and caller audit | Project owner | Seller Tools cleanup | Keep tools, delegate canonical rules |
| CV-OQ-014 | Is MI Business Intelligence v0.1 active or experimental? | Prevents duplicate Analytics owner | Versioned prototype exists | Usage, outputs, roadmap intent | Project owner | Analytics consolidation | Treat as experimental |
| CV-OQ-015 | Which launcher aliases/shortcuts are used on each PC? | Required before one-launcher cleanup | Three Putnam OS launchers; only one labeled CardVector production | Shortcut/scheduled task inventory | Project owner | Launcher alias removal | Keep all redirects |
| CV-OQ-016 | How should the current dirty Price Vector/eBay work be grouped and committed? | Architecture migration cannot begin on ambiguous source | Modified/untracked pricing, config, patch, backup files | Review diffs/tests and operator business folder | Project owner + implementing engineer | Phase 0 | No architecture implementation |
| CV-OQ-017 | Should public website source remain under `Docs`? | Docs changes trigger deployment and mix public source with project docs | Existing export workflow intentionally uses Docs and separate public repo | Team preference and workflow reliability | Project owner | Optional future site-source move | Keep current boundary |
| CV-OQ-018 | What desktop packaging/distribution is desired? | Affects pyproject dependencies and launcher/install behavior | Python/VBS works on current PCs | Installer/portable/venv expectations | Project owner | Final packaging, not bootstrap | Editable/source package plus VBS |
| CV-OQ-019 | What is the single application version source? | Current module versions differ | Putnam OS, MI, tools display separate versions | Release policy and independent subsystem version needs | Project owner + architect | Version consolidation | Preserve current versions until decision |
| CV-OQ-020 | How long must compatibility adapters remain? | Determines removal gates | Multiple legacy interfaces and two workstations | Release cadence and validation availability | Project owner | Adapter removal | Minimum two validated releases |

## Blocking Priority

### Blocks Phase 0

- CV-OQ-016

### Blocks Packaging/Entry Decisions

- CV-OQ-015
- CV-OQ-018
- CV-OQ-019

### Blocks Subsystem Consolidation

- CV-OQ-001
- CV-OQ-003
- CV-OQ-004
- CV-OQ-008
- CV-OQ-010
- CV-OQ-012
- CV-OQ-013

### Blocks Cleanup Only

- CV-OQ-002
- CV-OQ-005
- CV-OQ-006
- CV-OQ-011
- CV-OQ-014
- CV-OQ-017
- CV-OQ-020

### Future/Nonblocking

- CV-OQ-007

## Resolution Standard

When resolved:

1. add an Architecture Decision Log entry,
2. update the manifest/ownership matrix if affected,
3. record evidence and approval,
4. update the roadmap phase,
5. do not implement in the same decision-only commit unless separately approved.
