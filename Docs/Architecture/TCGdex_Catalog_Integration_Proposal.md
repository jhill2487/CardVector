# TCGdex catalog integration (review branch)

Scope: read-only external Pokémon card identification, without modifying Supabase,
seller inventory, checkout, deployment, or the public site.

Canonical implementation: `Platform/cardvector/integrations/tcgdex.py`.
The adapter exposes `get_card` and `search_cards`, and normalizes provider IDs,
names, set identity, local card number, language, and image references.

Example: `TCGdexCatalog().get_card("swsh7-215")` resolves the Umbreon VMAX
Evolving Skies 215/203 catalog identity. No condition, grading, print finish,
or market price is inferred from a catalog record.

**Not yet integrated into the web UI or Supabase.** Before doing so:
- Review the architecture change and catalog ownership with the project owner.
- Verify live TCGdex endpoint behavior and commercial asset usage.
- Test language coverage, variants and alternate finishes; never merge ambiguous printings.
- Define server-side caching, error handling and search limits.
- Keep CardUploader authoritative for seller inventory.
- Add integration tests and wire into the approved web application boundary.

Offline tests: `python -m unittest discover -s Tests -p "test_tcgdex_catalog.py"`
Rollback: close the PR or revert the commit; no data migration is required.
