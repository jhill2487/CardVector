# Phase 1.5 Working Tree Classification

All 27 changed or untracked files are classified. No unknown item remains.

## Tracked Changes

| Status | Path | Classification | Purpose and disposition | Blocks Phase 2 |
| --- | --- | --- | --- | --- |
| M | `Platform/Marketplace_Intelligence/marketplace_intelligence/__init__.py` | Active Price Vector/eBay source code | Public exports for canonical pricing/FMV work; preserve and checkpoint on feature branch | Yes |
| M | `Platform/Marketplace_Intelligence/marketplace_intelligence/bulk_export.py` | Active Price Vector/eBay source code | Uses explicit final listing price; preserve and checkpoint | Yes |
| M | `Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py` | Active Price Vector/eBay source code | Carries explicit FMV through analysis; preserve and checkpoint | Yes |
| M | `Platform/Marketplace_Intelligence/marketplace_intelligence/models.py` | Active Price Vector/eBay source code | Adds evidence, FMV, recommendation, final-price, and persisted-record models | Yes |
| M | `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py` | Active Price Vector/eBay source code | Canonical pricing delegation and explicit FMV implementation | Yes |
| M | `Platform/Marketplace_Intelligence/marketplace_intelligence/reports.py` | Active Price Vector/eBay source code | Reports distinct FMV/recommendation/final values | Yes |
| M | `Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_engine.py` | Active Price Vector/eBay source code | Legacy compatibility delegation | Yes |
| M | `Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_models.py` | Active Price Vector/eBay source code | Compatibility model aliases | Yes |
| M | `Platform/Putnam_OS/System/app/bulk_price_engine.py` | Active Price Vector/eBay source code | eBay active-listing revision through canonical pricing | Yes |
| M | `Platform/Putnam_OS/System/app/main.py` | Active Price Vector/eBay source code | Legacy UI handoff; contains the verified escaped-newline syntax defect | Yes |
| M | `Platform/Putnam_OS/System/app/putnam_os.py` | Active Price Vector/eBay source code | Production UI delegates pricing and adds active-listing revision handoff | Yes |
| M | `Platform/Putnam_OS/System/config/putnam_os_config.json` | Configuration | Non-secret marketplace URLs and pricing defaults used by the feature; checkpoint only on feature branch | Yes |

## Untracked Source, Tests, And Documentation

| Status | Path | Classification | Disposition | Blocks Phase 2 |
| --- | --- | --- | --- | --- |
| ?? | `Docs/PriceVector/current_code_audit.md` | Active Price Vector/eBay documentation | Commit on feature branch | Yes |
| ?? | `Docs/PriceVector/implementation_gap_map.md` | Active Price Vector/eBay documentation | Commit on feature branch | Yes |
| ?? | `Docs/PriceVector/overlay_extension_reuse_audit.md` | Active Price Vector/eBay documentation | Commit on feature branch | Yes |
| ?? | `Docs/PriceVector/phase_1_build_plan.md` | Active Price Vector/eBay documentation | Commit on feature branch | Yes |
| ?? | `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_repository.py` | Active Price Vector/eBay source code | Commit on feature branch | Yes |
| ?? | `Platform/Marketplace_Intelligence/migrations/001_price_vector_pricing_decisions.sql` | Active Price Vector/eBay source code | Versioned migration; commit on feature branch | Yes |
| ?? | `Platform/Marketplace_Intelligence/tests/test_price_vector_fmv_separation.py` | Active Price Vector/eBay tests | Commit on feature branch | Yes |
| ?? | `Platform/Marketplace_Intelligence/tests/test_pricing_engine_consolidation.py` | Active Price Vector/eBay tests | Commit on feature branch | Yes |

## Local-Only Artifacts

| Status | Path | Classification | Disposition | Blocks Phase 2 |
| --- | --- | --- | --- | --- |
| ?? | `Platform/Putnam_OS/System/app/bulk_price_engine.py.before_ebay_patch_20260717_132121.bak` | Backup artifact | Preserved in Phase 0 ZIP; keep outside Git and ignore | Yes until ignored |
| ?? | `Platform/Putnam_OS/System/app/main.py.before_ebay_patch_20260717_132121.bak` | Backup artifact | Preserved in Phase 0 ZIP; keep outside Git and ignore | Yes until ignored |
| ?? | `Platform/Putnam_OS/System/app/putnam_os.py.before_active_listing_fix_20260717_135604.bak` | Backup artifact | Preserved in Phase 0 ZIP; keep outside Git and ignore | Yes until ignored |
| ?? | `patch_cardvector_ebay_existing_listings.py` | Temporary developer tool | Preserved in Phase 0 ZIP; keep outside Git and ignore exact path | Yes until ignored |
| ?? | `Business/eBay_Store_Items/PIP Insurance Claims/Order 27-14693-04250/dedenne earnings.jpg` | Business-evidence image | Keep local and outside Git; ignore claims folder | Yes until ignored |
| ?? | `Business/eBay_Store_Items/PIP Insurance Claims/Order 27-14693-04250/dedenne not arrived.jpg` | Business-evidence image | Keep local and outside Git; ignore claims folder | Yes until ignored |
| ?? | `Business/eBay_Store_Items/PIP Insurance Claims/Order 27-14693-04250/order dedenne.jpg` | Business-evidence image | Keep local and outside Git; ignore claims folder | Yes until ignored |

There are no unclassified local databases, logs, caches, or runtime files in
the Git working-tree status.

## Final Disposition

| Initial group | Count | Resolution | Phase 2 blocker |
| --- | ---: | --- | --- |
| Tracked feature/config changes | 12 | Committed on `codex/checkpoint-price-vector-ebay-phase-1-5` | No |
| Untracked feature source/tests/docs | 8 | Committed on the same feature branch | No |
| Backup and patch artifacts | 4 | Preserved locally and in Phase 0 recovery; ignored on `main` | No |
| Business-evidence images | 3 | Preserved locally and by Phase 0 hashes; claims folder ignored | No |

Checkpoint commit:
`3dbadd593860a2847a8824106be9c1e41e74a76c`.

No item was deleted, moved, or left unknown. The "Blocks Phase 2" values in the
initial tables describe the state at capture time; the resolutions above remove
those blockers.
