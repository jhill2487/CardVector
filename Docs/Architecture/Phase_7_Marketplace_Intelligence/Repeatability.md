# Repeatability

`test_benchmark_is_exactly_repeatable` prices all 17 benchmark cases five
times through newly composed canonical pipelines.

The following values must match exactly on every run:

- final listing price
- confidence
- ordered reason codes
- review decision

The benchmark passed with identical snapshots. A fixed clock and explicit
fixture evidence prevent test results from depending on wall-clock time or an
external provider.

Production timestamps remain source evidence. If a future provider omits
capture or sale timestamps, the explanation reports `NO_RECENT_SALES` rather
than silently treating the evidence as recent.
