# Phase 3 FMV Characterization

## Current Formula

For legacy market reports, FMV requires at least three accepted comparables.
Available positive values are weighted:

- median: 60%
- last-three average: 30%
- last sale: 10%

Missing components cause the remaining weights to be renormalized. The result
is rounded to cents with `ROUND_HALF_UP`.

## Source Rules

- Condition-compatible eBay sold-comparable summaries are accepted.
- TCGplayer active listings are competition/reference evidence only.
- PriceCharting is not accepted for raw-card FMV.
- TCGtracking remains reference-only unless its existing configuration
  explicitly says otherwise.
- Currency remains USD; no conversion is performed.

## Missing Data And Confidence

- Fewer than three accepted market-report comparables: unavailable FMV.
- Unmatched or rejected provider data: unavailable FMV with retained evidence.
- Confidence values and reasoning are copied from the normalized evidence
  contract; Phase 3 adds no new scoring.

## Ownership

The canonical interface is
`Platform.cardvector.marketplace_intelligence.pricing`.
The tested algorithm remains physically in the historical pricing engine and
is re-exported without copying.

## Equivalence

All FMV characterization cases compare equal as dataclass values, including
evidence tuples, accepted count, confidence, reasoning, reference, currency,
and calculated timestamp behavior where a fixed fixture timestamp is used.
