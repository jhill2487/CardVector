# Phase 0 Working Tree Inventory

Captured: 2026-07-17T23:57:52-04:00

Status at capture: 12 tracked files modified, no staged files, and 39 untracked
files. Phase 0 report files created after this capture are intentionally not
part of the original inventory.

## Modified Tracked Files

| Status | Path | Classification | Purpose and preservation |
| --- | --- | --- | --- |
| `M` | `Platform/Marketplace_Intelligence/marketplace_intelligence/__init__.py` | Active Price Vector / eBay feature work | Exposes new FMV and pricing persistence interfaces. Intentional; preserve; eventually commit with validated feature work. |
| `M` | `Platform/Marketplace_Intelligence/marketplace_intelligence/bulk_export.py` | Active Price Vector / eBay feature work | Adapts export rows to explicit final listing price. Intentional; preserve. |
| `M` | `Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py` | Active Price Vector / eBay feature work | Builds explicit FMV before canonical recommendation. Intentional; preserve. |
| `M` | `Platform/Marketplace_Intelligence/marketplace_intelligence/models.py` | Active Price Vector / eBay feature work | Adds market evidence, FMV, pricing decision, and persisted record models. Intentional; preserve. |
| `M` | `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py` | Active Price Vector / eBay feature work | Consolidates canonical pricing and separates FMV, recommendation, and final price. Intentional; preserve. |
| `M` | `Platform/Marketplace_Intelligence/marketplace_intelligence/reports.py` | Active Price Vector / eBay feature work | Adds explicit pricing fields and evidence to reports. Intentional; preserve. |
| `M` | `Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_engine.py` | Active Price Vector / eBay feature work | Replaces duplicate formulas with delegation to Marketplace Intelligence. Intentional; preserve. |
| `M` | `Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_models.py` | Active Price Vector / eBay feature work | Compatibility export for the canonical pricing decision model. Intentional; preserve. |
| `M` | `Platform/Putnam_OS/System/app/bulk_price_engine.py` | Active Price Vector / eBay feature work | Uses canonical ladder logic and broadens active-listing CSV parsing. Intentional; preserve; validate before commit. |
| `M` | `Platform/Putnam_OS/System/app/main.py` | Active Price Vector / eBay feature work | Adds canonical pricing delegation and active-listing UI workflow. Intentional but incomplete: line 650 contains an unterminated f-string. Preserve as WIP; do not feature-commit yet. |
| `M` | `Platform/Putnam_OS/System/app/putnam_os.py` | Active Price Vector / eBay feature work | Delegates pricing and adds active-listing revision handoff. Intentional; preserve; validate with the complete feature. |
| `M` | `Platform/Putnam_OS/System/config/putnam_os_config.json` | Configuration | Changes CardUploader URL and adds eBay/mobile URLs plus pricing strategy thresholds. No absolute path or secret detected. Intentional-looking but requires owner review before any commit. Preserve exactly. |

## Untracked Architecture Documentation

All files below are intentional architecture audit or planning records. They
should be committed together, separate from feature work.

| Status | Path |
| --- | --- |
| `??` | `Docs/Architecture/CardVector_Architecture_Decision_Log.md` |
| `??` | `Docs/Architecture/CardVector_Architecture_Guardrails.md` |
| `??` | `Docs/Architecture/CardVector_Architecture_Manifest.md` |
| `??` | `Docs/Architecture/CardVector_Compatibility_Strategy.md` |
| `??` | `Docs/Architecture/CardVector_Configuration_Path_and_Runtime_Standards.md` |
| `??` | `Docs/Architecture/CardVector_Development_Standards.md` |
| `??` | `Docs/Architecture/CardVector_Entry_Point_and_Bootstrap_Standard.md` |
| `??` | `Docs/Architecture/CardVector_Future_Change_Process.md` |
| `??` | `Docs/Architecture/CardVector_Layering_and_Dependency_Rules.md` |
| `??` | `Docs/Architecture/CardVector_Migration_Roadmap.md` |
| `??` | `Docs/Architecture/CardVector_Open_Architecture_Questions.md` |
| `??` | `Docs/Architecture/CardVector_Subsystem_Ownership_Matrix.md` |
| `??` | `Docs/Architecture/CardVector_Target_Repository_Structure.md` |
| `??` | `Docs/Architecture/CardVector_Validation_and_Rollback_Standards.md` |
| `??` | `Docs/Architecture/CardVector_main_py_Retirement_Plan.md` |
| `??` | `Docs/Architecture/CardVector_putnam_os_Decomposition_Plan.md` |
| `??` | `Docs/Reports/Architecture_Audit.md` |
| `??` | `Docs/Reports/Architecture_Roadmap.md` |
| `??` | `Docs/Reports/Dead_Code_Report.md` |
| `??` | `Docs/Reports/Dependency_Map.md` |
| `??` | `Docs/Reports/Duplicate_Module_Report.md` |
| `??` | `Docs/Reports/Entry_Point_Report.md` |
| `??` | `Docs/Reports/Module_Ownership.md` |
| `??` | `Docs/Reports/Repository_Inventory.md` |

## Untracked Price Vector Files

| Status | Path | Classification | Purpose and preservation |
| --- | --- | --- | --- |
| `??` | `Docs/PriceVector/current_code_audit.md` | Active Price Vector / eBay feature work | Current-code evidence. Intentional; preserve with feature work. |
| `??` | `Docs/PriceVector/implementation_gap_map.md` | Active Price Vector / eBay feature work | Requirement gap map. Intentional; preserve. |
| `??` | `Docs/PriceVector/overlay_extension_reuse_audit.md` | Active Price Vector / eBay feature work | Overlay reuse audit. Intentional; preserve. |
| `??` | `Docs/PriceVector/phase_1_build_plan.md` | Active Price Vector / eBay feature work | Price Vector implementation plan. Intentional; preserve. |
| `??` | `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_repository.py` | Active Price Vector / eBay feature work | SQLite persistence for explicit pricing decisions. Intentional; preserve. |
| `??` | `Platform/Marketplace_Intelligence/migrations/001_price_vector_pricing_decisions.sql` | Active Price Vector / eBay feature work | Creates the Price Vector pricing-decision table and index. Intentional; preserve. |
| `??` | `Platform/Marketplace_Intelligence/tests/test_price_vector_fmv_separation.py` | Active Price Vector / eBay feature work | Tests explicit FMV/recommendation/final-price separation and persistence. Intentional; preserve. |
| `??` | `Platform/Marketplace_Intelligence/tests/test_pricing_engine_consolidation.py` | Active Price Vector / eBay feature work | Tests canonical pricing delegation and legacy compatibility. Intentional; preserve, currently blocked by `main.py` syntax. |

## Untracked Developer Artifacts

| Status | Path | Classification | Purpose and preservation |
| --- | --- | --- | --- |
| `??` | `Platform/Putnam_OS/System/app/bulk_price_engine.py.before_ebay_patch_20260717_132121.bak` | Developer tool output | Intermediate pre-patch backup; differs from HEAD and current source. Preserve in WIP archive, not a production commit; future ignore candidate. |
| `??` | `Platform/Putnam_OS/System/app/main.py.before_ebay_patch_20260717_132121.bak` | Developer tool output | Intermediate pre-patch backup; differs from HEAD and current source. Preserve in WIP archive; future ignore candidate. |
| `??` | `Platform/Putnam_OS/System/app/putnam_os.py.before_active_listing_fix_20260717_135604.bak` | Developer tool output | Intermediate pre-patch backup; differs from HEAD and current source. Preserve in WIP archive; future ignore candidate. |
| `??` | `patch_cardvector_ebay_existing_listings.py` | Developer tool output | One-time patch generator that created the backup files and source edits. Preserve for recovery review; do not commit as production source without explicit approval. |

## Untracked Business Evidence

These images are unrelated to architecture and feature source. Their folder
name indicates insurance-claim evidence and should be treated as potentially
sensitive business data. They remain in place, are not staged, and should not
be committed to the source repository without an explicit business-data policy.

| Status | Path | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `??` | `Business/eBay_Store_Items/PIP Insurance Claims/Order 27-14693-04250/dedenne earnings.jpg` | 44,365 | `943281537592FA535A22E142FB0C6D5EF67670B301C13A68EB18E50F05775324` |
| `??` | `Business/eBay_Store_Items/PIP Insurance Claims/Order 27-14693-04250/dedenne not arrived.jpg` | 88,028 | `838A0EC40FA3B44DC5FF1685CE1E00B869C720EF23C765A4F60C94EFB24CD2E1` |
| `??` | `Business/eBay_Store_Items/PIP Insurance Claims/Order 27-14693-04250/order dedenne.jpg` | 158,599 | `4C868E59533C3BD8CC17954BDFECF6F7045606F483DCDAFCCF6C9694F2D4BE82` |

## Ignored Areas Observed

Ignored runtime/output areas are listed in `Phase_0_Repository_State.md`.
Their contents were not enumerated as source changes and were not included in
the checkpoint commit plan.
