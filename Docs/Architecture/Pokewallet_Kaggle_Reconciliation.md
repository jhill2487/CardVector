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

## Import priority

Use `Tools/import_pokewallet_catalog.py` to fetch the authorized set catalog through documented paginated endpoints. **Process recent sets first**: use a verified set release date when present, then an explicit year in the set name. For undated sets, preserve PokéWallet directory order. The importer persists this order in its checkpoint, so a resumed batch does not restart or reshuffle prior progress. This priority applies to **all sets**, not only Mega Evolution Promos. The import does not update live card search or image mappings.

Example (admin-controlled environment with `POKEWALLET_API_KEY`):

```bash
python Tools/import_pokewallet_catalog.py --state private-pokewallet-checkpoint.json --catalog-output private-pokewallet-cards.json --max-requests 50 --interval-seconds 40
```

The importer is manually invoked and checkpoints each successful page. It does not create an unattended automation or have permission to publish images. Do not commit credentials or the private catalog to GitHub.

## Secure Development Dashboard progress (November 2026)

The administrator dashboard at `/status/` reads `public.cv_admin_job_progress`
from Supabase using the signed-in session. The table has RLS enabled and
read access is granted **only** when the authenticated JWT email is
`jhill2487@gmail.com`. Anonymous and other users have no read access.
No public browser may write progress; only a trusted server-side service-role
client can upsert the single `pokewallet-kaggle` record.

The importer persists local checkpoints and, when
`SUPABASE_SERVICE_ROLE_KEY` is configured **only in its trusted runtime**,
publishes aggregate counts after each successful batch. The API key must never
be embedded in HTML, frontend JavaScript, or the GitHub repository.

After reconciliation, the trusted operator can publish image counts:

```bash
python Tools/publish_import_progress.py --state private-pokewallet-checkpoint.json --summary reconciliation/summary.json
```

Until an authorized import actually runs, the table has no row and the
dashboard accurately reports **Not started**. Image match/review/missing
counts are not available until reconciliation finishes.

The `SUPABASE_SERVICE_ROLE_KEY` credential must be provisioned in the
trusted importing environment separately. GitHub Pages does not run
the importer and does not receive privileged credentials.
