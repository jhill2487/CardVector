# PokéWallet–Kaggle image reconciliation

Run across **all physical Pokémon TCG sets**, not just Mega Evolution Promos.

This is an offline, read-only process. It does not change CardVector search,
wanted requests, card identities, or existing images.

## Required input
- Cloudflare R2 `archive/card-image-index.csv` (21,199 indexed files at last audit).
- A licensed/authorized **complete PokéWallet card export** in JSON, using the
  card records returned by its API (`card_info.name`, `set_name`,
  `card_number`, `set_id`).
- Optional manually reviewed set alias JSON mapping PokéWallet set labels to
  exact Kaggle folder names.

CardVector's currently deployed PokéWallet Edge Function supports creator-only
authenticated **single-card searches** and image lookups. It does **not**
currently expose an authenticated bulk catalog export. Do not scrape thousands
of queries or expose the API key to the browser. Obtain an approved complete
catalog export/feed or add an admin-only, rate-limited import workflow after
confirming provider permissions and API limits. Partial data cannot justify
claiming all sets have been reconciled.

## Run

```bash
python Tools/reconcile_pokewallet_kaggle.py \
  --pokewallet pokewallet_cards.json \
  --kaggle-index card-image-index.csv \
  --set-aliases reviewed_set_aliases.json \
  --output reconciliation
```

Outputs: `matched.json`, `needs_review.json`, `missing.json`,
`summary.json`. A unique filename/set/number match can become a proposed
mapping; finish conflicts or mismatched names require human verification.
**Do not publish mappings automatically.** Explicit review is required before
a later version is allowed to update a public manifest or database.

Do not commit any private API keys or unlicensed raw provider exports.
