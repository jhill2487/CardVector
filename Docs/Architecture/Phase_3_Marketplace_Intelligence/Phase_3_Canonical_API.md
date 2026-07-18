# Phase 3 Canonical API

## Approved Public Root

`Platform.cardvector.marketplace_intelligence`

New production callers must import through this root or its documented
submodules. The historical implementation remains behind aliases during the
delegation-first migration.

## Public Modules

| Module | Responsibility |
| --- | --- |
| `models` | Stable pricing, FMV, evidence, listing, result, and persistence contracts |
| `pricing` | Proven FMV and Price Vector functions and `PricingEngine` |
| `service` | Dependency-injectable `PricingService` and `PRICING_SERVICE` facade |
| `evidence` | Pure Putnam comparable interpretation and injected sales-row analysis |
| `persistence` | Pricing-decision repository, migration path, and record mapper |
| `adapters` | Stable aliases for existing CardUploader, eBay-sales-cache, and TCGtracking normalization providers |

## Calculation Operations

- `fair_market_value_from_market_report(...)`
- `fair_market_value_from_market_price(...)`
- `calculate_market_value(...)` compatibility value
- `apply_pricing_strategy(...)`
- `build_pricing_decision_from_fmv(...)`
- `build_pricing_decision(...)` compatibility report adapter
- `PricingEngine.recommend_from_fmv(...)`
- `optimized_export_price(...)`
- `normalize_price_ladder(...)`
- `apply_exact_price_ladder(...)`
- `evaluate_new_listing_price(...)`

`determine_final_price`, confidence evaluation, and bulk repricing were not
invented as separate APIs. Current behavior already produces those values
inside the existing recommendation and ladder contracts.

## Application Boundary

`Platform.cardvector.application.PricingApplication` accepts an injected
`PricingOperations` protocol. It contains no pricing mathematics and does not
import a concrete Marketplace Intelligence implementation.

Current composition in `putnam_os.py` is:

```text
PricingApplication(PRICING_SERVICE)
```

The object is registered in `ApplicationRuntime.services` as `pricing`.

## Exceptions And Serialization

Current exception behavior remains native:

- unknown strategy: `ValueError`
- invalid caller money parsing in legacy bulk workflows: existing
  `InvalidOperation` handling
- persistence failures: existing SQLite exceptions

Serialization remains owned by the proven dataclasses and report/repository
functions. No field names or formats changed.
