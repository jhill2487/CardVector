# Phase 3 Repository State

## Scope

This report records the verified starting state for Phase 3 Marketplace
Intelligence Consolidation. It is evidence, not permission for another
subsystem migration.

## Verified Baseline

| Item | Observed value |
| --- | --- |
| Branch | `main` |
| HEAD | `c289a979ac3ee251d729fa9f288a06afb4d51573` |
| Upstream | `origin/main` |
| Ahead / behind | 8 ahead / 0 behind |
| Working tree | Clean |
| Git operation | No merge, rebase, cherry-pick, or revert in progress |
| Recovery reference | `cardvector-pre-price-vector-integration` |
| Production launcher | `Platform/Putnam_OS/Run CardVector OS Production.vbs` |
| Production Python target | `Platform/Putnam_OS/System/app/putnam_os.py` |
| Launcher SHA-256 | `AD5044D8D439CE6B321951E85A335DE86927AAA9453FE05DF0A23C1327006EE7` |
| Architecture checker | 48 documented pre-existing findings; 0 new findings |

## Required Baseline Components

The following were present before Phase 3 changes:

- `Platform/cardvector/application/`
- `Docs/Architecture/Phase_2_Application/`
- `Docs/Architecture/Price_Vector_Integration_Gate/`
- Price Vector integration commit
  `aaf9a0f49b779a02f720fd99610183a5026b5ef9`
- Separate FMV, recommended-listing-price, and final-listing-price contracts
- SQLite pricing-decision repository and migration
- Putnam OS pricing delegation to
  `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`

## Starting Dependency Chain

```text
putnam_os.py / main.py / bulk_price_engine.py
    -> Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_engine
    -> pricing calculations and result models
```

Phase 2 workflow-context calls already use:

```text
putnam_os.py
    -> Platform.cardvector.application
    -> injected legacy workflow-context delegates
```

## Starting Risks

1. The approved future package
   `Platform/cardvector/marketplace_intelligence/` does not yet exist.
2. The proven pricing implementation is canonical in behavior but remains at
   its historical package path.
3. `putnam_os.py` still contains comparable filtering, evidence interpretation,
   confidence calculation, and marketplace-analysis orchestration.
4. The Listing Optimizer retains a duplicate low-price tier calculation.
5. Current application-layer dependency tests predate the approved Phase 3
   public subsystem dependency.
6. Historical backups contain duplicate formulas but are not production
   callers and remain out of Phase 3 cleanup scope.

## Protected Boundaries

Phase 3 must not alter:

- production launcher files or targets,
- capture, inventory, orders, shipping, or recognition behavior,
- eBay or TCGplayer live data,
- production databases,
- CSV schemas or output filenames,
- pricing formulas, thresholds, rounding, confidence, or error categories,
- `main.py` public entry behavior.
