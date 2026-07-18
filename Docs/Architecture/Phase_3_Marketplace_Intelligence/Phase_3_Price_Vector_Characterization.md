# Phase 3 Price Vector Characterization

## Inputs

Price Vector consumes an explicit `FairMarketValue` in its primary path.
`build_pricing_decision(...)` remains a compatibility adapter that first maps a
legacy market report into FMV.

## Preserved Rules

- strategies: market match, fast sell, and profit
- default export floor: `0.99`
- configured percentage and amount increase/decrease constraints
- shipping assumptions
- configured cent/ending rounding
- confidence review and auto-apply thresholds
- exact legacy active-listing ladder
- high-value new-listing review behavior

Acquisition margin is not part of the current recommendation contract and was
not added.

## Outputs

The following remain distinct:

- `fair_market_value`
- `recommended_listing_price`
- `final_listing_price`

With no override, final listing price continues to default to the
recommendation according to the existing contract.

Compatibility aliases `market_value` and `recommended_price` remain intact.
No threshold, status, field, error, or rounding behavior changed.

## Deferred Legacy Formula

`putnam_listing_optimizer_v1_1.py` contains an overlapping low-price tier.
It was not modified because its direct-script loading and mixed listing/export
responsibilities require a separately characterized adapter. It is registered
as a compatibility/deprecation candidate, not selected as a second canonical
engine.
