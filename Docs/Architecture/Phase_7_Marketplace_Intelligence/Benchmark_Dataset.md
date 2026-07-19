# Benchmark Dataset

Fixture:
`Tests/marketplace_intelligence/fixtures/phase7_benchmark.json`

The versioned dataset contains 17 synthetic, non-live cases covering:

- modern and vintage Pokemon
- promos and reverse holos
- special illustration, illustration, secret, and trainer-gallery cards
- EX, GX, V, and VMAX
- low-value and high-value prices
- stable and high-volatility markets
- low-confidence evidence

Each case includes identity, current price, explicit fixture FMV, confidence,
accepted and rejected counts, average, range, variant, finish, and expected
final price. The provider is injected and performs no file, network, account,
or marketplace activity.

The fixture clock is fixed at 2026-07-19 so stale-market reasoning remains
repeatable across future test runs.
