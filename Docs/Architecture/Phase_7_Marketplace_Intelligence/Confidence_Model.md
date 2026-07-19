# Confidence And Review Model

Provider confidence remains unchanged. CardUploader sold-cache confidence is
the sum of:

- accepted-comparable count: up to 45 points
- last-three spread: up to 25 points
- identity completeness: 25 points with set evidence, otherwise 15

The canonical explanation policy maps textual confidence as high 85, medium
70, low 50, reference 40, and none 0. Numeric confidence remains numeric.

## Configurable Advisory Thresholds

| Setting | Default | Meaning |
| --- | ---: | --- |
| `auto_approve_confidence` | 80 | Eligible for advisory auto approval when no warning applies |
| `manual_review_below_confidence` | 60 | Manual review boundary |
| `warning_below_confidence` | 70 | Pricing warning boundary |
| `insufficient_data_comps` | 3 | Insufficient comparable count |
| `stale_market_days` | 30 | Stale market boundary |
| `price_spike_percent` | 40 | Increase warning |
| `price_collapse_percent` | 40 | Decrease warning |
| `high_variance_percent` | 35 | Range-to-median variance warning |
| `review_price_over` | 100 | Existing Price Vector high-price review threshold |

Advisory decisions are `AUTO_APPROVE`, `REVIEW_RECOMMENDED`,
`PRICING_WARNING`, `MANUAL_REVIEW`, and `INSUFFICIENT_DATA`.

Phase 7 does not change the legacy `Decision.changed`, bulk-revise inclusion,
or Price Vector calculation. Advisory review output prepares Phase 8; it does
not update a listing.
