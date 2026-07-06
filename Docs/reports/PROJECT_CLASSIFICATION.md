# CardVector Project Classification

Generated: 2026-07-06

Package: Phase 0 Cleanup Package 00 - Project Classification

Purpose: permanent project governance metadata for future Codex sessions and
cleanup planning.

Scope: classification only. This document does not recommend cleanup,
restructuring, file moves, folder moves, renames, refactors, import changes, or
application behavior changes.

## Classification Legend

- Production: trusted or intended for daily business operation.
- Active Development: currently evolving and expected to receive feature work.
- Shared Platform: reusable infrastructure or common support for multiple
  modules.
- Business Data: operating files, source CSVs, inventory records, or business
  working material.
- Generated Runtime: captures, reports, logs, exports, caches, or generated
  outputs.
- Historical Archive: old versions, backups, checkpoints, or preserved
  historical work.
- Legacy Reference: older implementation retained for reference or compatibility.
- Experimental: research, prototype, shadow-mode, or validation work.
- Unknown: purpose not yet confirmed.

## Major Root Areas

| Area | Purpose | Classification | Canonical Owner | Should future work extend this location? | Risk if modified | Notes |
|---|---|---|---|---:|---:|---|
| `Platform/` | Houses CardVector applications, shared platform code, and reusable modules. | Shared Platform | CardVector Platform | YES | HIGH | Primary software development area. Future application work should normally occur here through existing owners. |
| `Business/` | Daily operating business files such as eBay store items and inventory working files. | Business Data | Putnam Collectibles Business Operations | YES | HIGH | Treat as business operating data. Changes can affect listing, pricing, and audit work. |
| `Data/` | Shared imports, exports, logs, media, processed outputs, config, and generated data. | Generated Runtime | CardVector Platform / Putnam Collectibles Operations | YES | HIGH | Extend only for generated/runtime outputs and portable configuration. Do not treat as source code. |
| `Docs/` | Governance, standards, reports, roadmap, status, and project documentation. | Shared Platform | Project Governance | YES | MEDIUM | Permanent governance lives here. Documentation changes should preserve hierarchy and current standards. |
| `Tools/` | Standalone helper utilities and validation tooling. | Shared Platform | CardVector Platform Tools | YES | MEDIUM | Suitable for standalone tools that are not app entry points or core modules. |
| `Archive/` | Preserved old versions, backups, historical experiments, datasets, and checkpoints. | Historical Archive | Project Archive | NO | HIGH | Reference and preservation area. Future work should read from here when needed, not extend it for active features. |
| `Work_Sessions/` | Work-session records, session logs, temporary work products, and development notes. | Generated Runtime | Putnam Collectibles Operations / Project History | YES | MEDIUM | Extend only by writing new work-session records or notes. Do not treat as application source. |
| `Capture/` | Capture Studio session folders and captured card images. | Generated Runtime | CardVector Capture Studio | YES | HIGH | Active production/runtime image output. Future capture workflows may write here; do not manually alter session contents casually. |
| `Putnam_Content/` | Content workflow materials such as ideas, recordings, clips, and episodes. | Business Data | Putnam Collectibles Content Operations | YES | MEDIUM | Business/content operating area. Extend only for content workflow needs. |
| `Shared/` | Shared templates or resources used by tools/workflows. | Shared Platform | CardVector Shared Resources | YES | MEDIUM | Purpose appears shared/template-oriented. Confirm owner before adding broad new shared assets. |
| `Collectr/` | Purpose not confirmed from Phase 0 inspection. | Unknown | Unknown | NO | HIGH | Do not extend until the user confirms its role. |
| `Putnam_Platform/` | Root-level platform-looking folder that overlaps conceptually with `Platform/Putnam_Platform/`. | Legacy Reference | Unknown / Legacy Putnam Platform | NO | HIGH | Treat as legacy/reference unless confirmed active. Do not extend for new CardVector work. |
| `Putnam_Seller_Tools/` | Root-level seller/business intelligence and branding materials. | Legacy Reference | Putnam Seller Tools / Business Intelligence | NO | MEDIUM | May contain useful BI/branding work. Do not extend until ownership relative to `Platform/Putnam_OS/Putnam_Seller_Tools/` is confirmed. |
| `.agents/` | Agent/session metadata folder. | Generated Runtime | Agent Tooling | NO | MEDIUM | Agent-managed area. Do not use for project source. |
| `.git/` | Version control metadata. | Shared Platform | Git | NO | HIGH | Do not modify manually. |

## Platform Application Areas

| Area | Purpose | Classification | Canonical Owner | Should future work extend this location? | Risk if modified | Notes |
|---|---|---|---|---:|---:|---|
| `Platform/Putnam_OS/` | CardVector OS application, production workflow orchestration, inventory, capture UI, import, pricing/export handoff, orders, and business operations. | Production | CardVector OS | YES | HIGH | Current production app area. Extend existing modules only and preserve validated workflow. |
| `Platform/Putnam_OS/System/app/` | Main CardVector OS Python application and focused app services. | Production | CardVector OS Application | YES | HIGH | Contains active entry point and services. Future work here requires careful inspection and tests. |
| `Platform/Putnam_OS/System/app/putnam_os.py` | Main CardVector OS Tk application shell and workflow orchestrator. | Production | CardVector OS | YES | HIGH | Current canonical app entry point; large and high-risk. |
| `Platform/Putnam_OS/System/app/capture_studio.py` | Capture Studio service for capture sessions, manual capture, OBS screenshots, retakes, and session files. | Production | CardVector Capture Studio | YES | HIGH | Extend for capture service behavior only. Card recognition stays outside this module. |
| `Platform/Putnam_OS/System/app/obs_connection_manager.py` | Shared OBS WebSocket connection manager. | Production | CardVector Capture Studio / Shared OBS Service | YES | HIGH | Canonical OBS connection service. Future OBS work should reuse this path. |
| `Platform/Putnam_OS/System/app/inventory_locations.py` | ETB/container registry, ETB statuses, capacity estimates, and simple HTML labels. | Production | CardVector OS Inventory | YES | HIGH | Owns ETB location registry behavior. Keep separate from card identification. |
| `Platform/Putnam_OS/System/app/orders_fulfillment.py` | eBay orders CSV parsing and pick slip generation. | Production | CardVector OS Orders | YES | MEDIUM | Focused service module for fulfillment foundation. |
| `Platform/Putnam_OS/System/app/bulk_price_engine.py` | Existing listing price revision support inside CardVector OS. | Legacy Reference | CardVector OS / Pricing Compatibility | NO | HIGH | Pricing ownership overlaps Marketplace Intelligence. Treat as compatibility/reference unless specifically tasked. |
| `Platform/Putnam_OS/System/tools/` | CardVector OS-specific helper tools, including ETB QR label generator. | Active Development | CardVector OS Tools | YES | MEDIUM | Extend for OS-local tools only when they support existing workflows. |
| `Platform/Putnam_OS/System/data/` | Internal CardVector OS persistent data such as acquisitions, inventory audit, and market cache. | Business Data | CardVector OS Data | YES | HIGH | Application-managed data. Do not manually rewrite without a migration plan. |
| `Platform/Putnam_OS/System/config/` | CardVector OS configuration files. | Production | CardVector OS Configuration | YES | HIGH | Active config location for app behavior. Changes can alter production workflow. |
| `Platform/Putnam_OS/System/logs/` | CardVector OS internal logs. | Generated Runtime | CardVector OS Runtime | YES | MEDIUM | Runtime output. Extend only by logging from active workflows. |
| `Platform/Putnam_OS/System/cache/` | CardVector OS cache data. | Generated Runtime | CardVector OS Runtime | YES | MEDIUM | Cache/runtime area. Should not contain source logic. |
| `Platform/Putnam_OS/System_Archive/` | CardVector OS release checkpoints, backups, and patch archives. | Historical Archive | CardVector OS Archive | NO | HIGH | Preserve. Future work should not extend except by explicit checkpoint/backup tasks. |
| `Platform/Putnam_OS/Completed Jobs/` | Completed CardVector OS job outputs. | Generated Runtime | CardVector OS Runtime | YES | HIGH | Business-relevant generated outputs. Do not modify casually. |
| `Platform/Putnam_OS/Incoming Files/` | Incoming workflow files for CardVector OS. | Generated Runtime | CardVector OS Runtime | YES | MEDIUM | Runtime intake/output area. Source code does not belong here. |
| `Platform/Putnam_OS/Putnam_Seller_Tools/` | Seller audit, SKU repair planner, listing optimizer reference, and location registry support tools. | Active Development | CardVector OS Seller Tools | YES | HIGH | Canonical-looking seller tools location for OS-adjacent tools. Extend existing tools rather than duplicating. |
| `Platform/Putnam_OS/Putnam_Listing_Optimizer/` | Listing optimizer support/reference area under CardVector OS. | Legacy Reference | CardVector OS Listing Workflow | NO | MEDIUM | Current status indicates legacy optimizer is retired from active operator workflow. |
| `Platform/Marketplace_Intelligence/` | Standalone Marketplace Intelligence desktop app and reusable pricing/market engine package. | Active Development | CardVector Pricing Engine / Marketplace Intelligence | YES | HIGH | Intended reusable pricing intelligence area. Preserve standalone nature and no inventory dependency. |
| `Platform/Marketplace_Intelligence/marketplace_intelligence/` | Marketplace Intelligence Python package: import, parser, provider, pricing, decision, reports, UI. | Active Development | CardVector Pricing Engine | YES | HIGH | Future pricing-engine work should extend this package when applicable. |
| `Platform/Marketplace_Intelligence/config/` | Marketplace Intelligence configuration and source profiles. | Active Development | Marketplace Intelligence Configuration | YES | MEDIUM | Strategy/profile changes belong in config when possible, not code. |
| `Platform/Marketplace_Intelligence/reports/` | Marketplace Intelligence generated reports. | Generated Runtime | Marketplace Intelligence Runtime | YES | MEDIUM | Generated output. Do not treat as source. |
| `Platform/Marketplace_Intelligence/backups/` | Marketplace Intelligence backups/checkpoints. | Historical Archive | Marketplace Intelligence Archive | NO | MEDIUM | Preserve unless retention policy says otherwise. |
| `Platform/Marketplace_Intelligence/examples/` | Sample CSV/config data for Marketplace Intelligence. | Active Development | Marketplace Intelligence Examples | YES | LOW | Safe to extend with small non-sensitive examples when needed. |
| `Platform/Marketplace_Intelligence/tests/` | Marketplace Intelligence tests. | Active Development | Marketplace Intelligence Tests | YES | MEDIUM | Extend with tests for engine behavior. |
| `Platform/Putnam_Platform/` | Older platform tools, capture utilities, engines, initializer, and decision-engine experiments. | Legacy Reference | Legacy Putnam Platform | NO | HIGH | Contains useful reference code but overlaps current CardVector ownership. New work should prefer current canonical owners. |
| `Platform/Putnam_Platform/capture/` | Legacy/support capture CLI, OBS autocrop bridge, capture settings, and docs. | Legacy Reference | Legacy Capture Tools | NO | HIGH | Current Capture Studio owner is under `Platform/Putnam_OS/System/app/`. |
| `Platform/Putnam_Platform/Decision_Engine/` | Earlier decision-engine modules for content, inventory, marketplace, pricing, velocity. | Legacy Reference | Legacy Decision Engine | NO | HIGH | Pricing/decision ownership overlaps Marketplace Intelligence. Do not extend unless specifically reviving legacy engine. |
| `Platform/Putnam_Platform/engines/` | Legacy Bulk Price Engine and Market Intelligence engines. | Legacy Reference | Legacy Pricing / Market Engines | NO | HIGH | Treat as historical/reference until ownership decisions are final. |
| `Platform/Putnam_Platform/tools/` | Legacy platform maintenance and launcher scripts. | Legacy Reference | Legacy Platform Tools | NO | MEDIUM | Use only when known active. Prefer current path manager and current tools for new work. |
| `Platform/Pokemon_Live_Price_Lookup/` | Pokemon lookup overlay / lookup backend area. | Active Development | Pokemon Lookup Overlay | YES | MEDIUM | Independent product area. Extend only for overlay-specific lookup work. |
| `Platform/putnam_paths.py` | Central repository-aware path manager. | Shared Platform | CardVector Platform Path Manager | YES | HIGH | Canonical shared path resolver. New path behavior should extend this carefully. |
| `Platform/__pycache__/` | Python bytecode cache. | Generated Runtime | Python Runtime | NO | LOW | Runtime cache, not source. |

## Business And Data Areas

| Area | Purpose | Classification | Canonical Owner | Should future work extend this location? | Risk if modified | Notes |
|---|---|---|---|---:|---:|---|
| `Business/eBay_Store_Items/` | eBay active listings and store item CSV/report inputs. | Business Data | Putnam Collectibles eBay Operations | YES | HIGH | Source business data. Never modify source CSVs during audits unless explicitly requested. |
| `Business/Inventory/` | Business inventory working files and pricing revision materials. | Business Data | Putnam Collectibles Inventory Operations | YES | HIGH | Operational data. Changes can affect inventory decisions. |
| `Data/Imports/` | Imported files and copied source inputs for workflows. | Generated Runtime | CardVector Runtime | YES | MEDIUM | Application-managed import area. |
| `Data/Exports/` | Generated exports, labels, pick lists, reports, and eBay-ready files. | Generated Runtime | CardVector Runtime | YES | HIGH | Business-relevant outputs. Do not overwrite or delete casually. |
| `Data/Logs/` | Shared platform and workflow logs. | Generated Runtime | CardVector Runtime | YES | MEDIUM | Runtime logging area. |
| `Data/Media/` | Shared media outputs or business media. | Generated Runtime | CardVector Runtime / Business Media | YES | MEDIUM | Suitable for media outputs when workflow-owned. |
| `Data/Processed/` | Processed images, smoke-test outputs, autocrop outputs, and derived data. | Generated Runtime | CardVector Runtime | YES | MEDIUM | Generated data. Do not treat as source. |
| `Data/Config/` | Shared data-layer configuration such as ETB location registry and import state. | Shared Platform | CardVector Configuration | YES | HIGH | Active configuration. Modify only through intended workflows or explicit tasks. |

## Documentation Areas

| Area | Purpose | Classification | Canonical Owner | Should future work extend this location? | Risk if modified | Notes |
|---|---|---|---|---:|---:|---|
| `Docs/Reports/` | Phase reports, audits, plans, and governance reports. | Shared Platform | Project Governance Reports | YES | LOW | Correct location for audit and planning documents. |
| `Docs/Putnam_Standards/` | Highest-level standards and templates below Putnam Principles/platform vision. | Shared Platform | Project Governance | YES | HIGH | Changes affect future agent behavior. Edit only with explicit governance tasks. |
| `Docs/Putnam_Standards/templates/` | Governance/documentation templates. | Shared Platform | Project Governance | YES | LOW | Extend with templates when standards require it. |

## Supporting / Unknown Areas

| Area | Purpose | Classification | Canonical Owner | Should future work extend this location? | Risk if modified | Notes |
|---|---|---|---|---:|---:|---|
| root `AGENTS.md` | Agent entry stub pointing to canonical documentation. | Shared Platform | Project Governance | YES | HIGH | Keep minimal and discoverable for agents. |
| `.putnam_root` | Repository root marker. | Shared Platform | CardVector Platform Path Manager | NO | HIGH | Required for path discovery. |
| root `PLATFORM_VISION.md` | Locked CardVector platform vision. | Shared Platform | Platform Governance | YES | HIGH | High-level architecture document. Edit only by explicit governance task. |
| root `cardvector_*` scripts and `CARDVECTOR_*` reports | Prior audit scripts and report artifacts. | Historical Archive | Project Audit History | NO | LOW | Existing root artifacts are not current app code. This classification does not recommend moving them. |
| root `ScreenRecording_06-30-2026 14-42-57_1.MP4` | Large media artifact at root. | Generated Runtime | Unknown / Work Session Media | NO | MEDIUM | Treat as media/runtime until owner is confirmed. |

## Governance Notes

- Future Codex sessions should read this classification before executing any
  cleanup package.
- Classification does not imply permission to modify a location.
- `YES` means future work may extend the location when the task belongs to that
  owner and follows governance.
- `NO` means future work should avoid extending the location unless a later
  governance decision changes its role.
- High-risk areas may still be canonical. High risk means changes require
  stronger validation and clearer rollback.
- Unknown areas should not receive new work until their purpose and owner are
  confirmed by the user.

