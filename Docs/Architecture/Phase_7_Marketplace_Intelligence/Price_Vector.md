# Price Vector

## Current Production Mathematics

The current engine remains unchanged:

1. Legacy market reports require at least three accepted comparables.
2. FMV uses median at 60 percent, last-three average at 30 percent, and last
   sale at 10 percent, renormalized over available values.
3. Explicit provider FMV is passed into Price Vector without re-reading raw
   evidence.
4. Shipping assumptions, market strategy, increase/decrease caps, minimum
   price, rounding, ignored-small-change threshold, and review checks are
   applied in that order.
5. Recommended and final price remain separate fields; final defaults to the
   recommendation.

The sold-cache provider currently uses the median of the first 20 accepted
cached results. It reports average, low, high, duplicates observed, and zero
outliers removed, but these added facts do not change the median.

## Current Limitations

- No recency weighting
- No volume weighting
- No statistical outlier rejection
- No currency conversion; USD is assumed
- No condition-specific adjustment beyond source matching
- No graded-card methodology
- No acquisition-margin input

## Recommended Improvements

Any future math change should be separately approved and benchmarked. The
safest sequence is: add sale timestamps and unique sale IDs, deduplicate,
introduce a documented robust outlier strategy, then evaluate recency weighting
against the Phase 7 benchmark. The previous and candidate outputs must be
reported side by side before a formula changes.
