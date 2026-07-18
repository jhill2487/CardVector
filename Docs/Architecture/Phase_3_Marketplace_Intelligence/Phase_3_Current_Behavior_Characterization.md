# Phase 3 Current Behavior Characterization

## Purpose

The characterization suite captured pricing and evidence behavior before
production callers were redirected. It uses local fixtures and temporary
databases only.

## Characterized Contracts

| Area | Cases fixed by tests |
| --- | --- |
| FMV availability | no report, empty report, fewer than three accepted comps, missing weighted values |
| FMV weighting | median 60%, last-three average 30%, last sale 10%; available weights are renormalized |
| FMV evidence | eBay sold summaries accepted; TCGplayer active listings and PriceCharting raw values rejected |
| Currency | USD; no conversion |
| Price Vector | market match, fast sell, profit, unknown-strategy error |
| Confidence | exact low/high review thresholds and status values |
| Constraints | floor, percentage/amount caps, shipping assumption, rounding |
| Listing workflows | low-price export boundaries, exact ladder, high-value review |
| Bulk errors | invalid rows remain separately classified |
| Evidence matching | accepted, graded, name, number, set, and non-single rejection behavior |
| Persistence | exact temporary SQLite save/get round trip |
| Serialization | exact report field order and distinct FMV/recommended/final values |

## Fixed Representative Values

- Weighted report `{median: 5.00, last3_avg: 5.50, last_sale: 4.50}`
  produces FMV `5.10`.
- A missing last-three value with median `5.00` and last sale `4.00`
  produces FMV `4.86`.
- Confidence `59` keeps final price `3.99` and status
  `MANUAL_REVIEW_REQUIRED`.
- Confidence `80` applies final price `5.10` and status `AUTO_APPLIED`.
- Optimized export boundaries remain:
  `0.50 -> 0.99`, `1.50 -> 0.99`, `1.51 -> 1.49`,
  `2.99 -> 1.49`, `3.00 -> 2.99`, `4.99 -> 2.99`,
  `5.00 -> 5.00`.
- The existing duplicate and outlier behavior remains intentionally
  unchanged: cached prices `1.00`, `1.00`, `100.00` produce median `1.00`
  and last-three average `34.00`.

## Evidence

- `Tests/marketplace_intelligence/test_phase3_characterization.py`
- `Platform/Marketplace_Intelligence/tests/test_price_vector_fmv_separation.py`
- `Platform/Marketplace_Intelligence/tests/test_pricing_engine_consolidation.py`

The pre-migration characterization run passed 19 tests. The post-migration
combined characterization and canonical-contract run passed with exact
equality.
