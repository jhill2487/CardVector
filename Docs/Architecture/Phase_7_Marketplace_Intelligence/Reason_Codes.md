# Pricing Reason Codes

| Code | Meaning |
| --- | --- |
| `NO_MARKET_DATA` | No usable FMV was produced |
| `LOW_DATA` | Comparable count is below the configured minimum |
| `HIGH_VARIANCE` | Observed price range exceeds the configured variance threshold |
| `NO_RECENT_SALES` | Comparable evidence lacks a source sale/capture timestamp |
| `STALE_MARKET` | Evidence age exceeds the configured stale-market threshold |
| `PROMO_VARIANT` | Identity indicates a promotional card |
| `VARIANT_UNVERIFIED` | Listing variant/finish is not proven by provider metadata |
| `REFERENCE_ONLY` | Evidence is supporting information and cannot drive FMV |
| `HIGH_CONFIDENCE` | Confidence reaches the auto-approve threshold |
| `LOW_CONFIDENCE` | Confidence is below the warning threshold |
| `PRICE_SPIKE` | Recommended increase exceeds the configured threshold |
| `PRICE_COLLAPSE` | Recommended decrease exceeds the configured threshold |
| `REVIEW_REQUIRED` | Existing or advisory review policy requires attention |
| `MARKET_ALIGNED` | No other warning or special reason applies |

Codes are deterministic, ordered, deduplicated, serialized as a JSON list, and
exported to CSV as semicolon-separated values. They explain a result but do not
replace the existing human-readable pricing and decision reasons.
