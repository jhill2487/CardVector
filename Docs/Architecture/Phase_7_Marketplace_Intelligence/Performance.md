# Performance

## Fixture Profile

Environment: bundled local Python, fixture-only provider, 2026-07-19.

- Listings: 1,000
- Elapsed: 0.751852 seconds
- Mean pipeline time: 0.7519 ms per listing
- Peak traced memory: 3,454,127 bytes
- Provider calls: 1,000

These measurements characterize local CPU work; they do not claim live API
latency.

## Cache

The CardUploader/eBay sold-cache provider previously reread unchanged JSON for
every lookup. Phase 7 adds an mtime-aware in-memory document cache:

- first unchanged lookup: one miss and one read
- second unchanged lookup: one hit and no read
- file mtime change: reload on the next lookup

The cache does not change comparable filtering or price results. It exposes hit
and miss counters for profiling.

## Future Optimizations

- cache normalized identity-to-cache-path resolution
- index unique sale IDs after the data contract supplies them
- batch provider lookups when a supported API exists
- bound long-running cache size if the number of cache files grows materially

No live API usage or browser automation was measured.
