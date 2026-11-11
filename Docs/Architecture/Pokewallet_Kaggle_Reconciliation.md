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

## Automatic daily importer — 750 card printings per day

GitHub Actions workflow `.github/workflows/daily-pokewallet-import.yml` runs
automatically every day at **14:17 UTC**. No manual trigger is needed. It imports
**up to 750 eligible card records per day**, including unique PokéWallet
printings and excluding sealed products. The first run loads all PokéWallet
sets and prioritizes the most recent release dates. Older sets follow once
recent sets are complete. The importer stops after 750 eligible records and
resumes from the exact set, page and **in-page offset** the next day.

The workflow uses at most 40 PokéWallet API requests per execution, spaced
at least 45 seconds apart. This respects a conservative share of the free tier's
100 requests/hour and 1000/day (other usage of the same key still shares quota).
The schedule may be delayed by GitHub Actions. Rate-limit and API failures stop
the run rather than silently skipping records; successful page checkpoints are
preserved for the next run.

The **only setup required before the first run** is adding two GitHub
repository Actions secrets to `jhill2487/CardVector`:

- `POKEWALLET_API_KEY` — the existing PokéWallet API key used by CardVector
- `SUPABASE_SERVICE_ROLE_KEY` — server-side Supabase service-role key

Never paste these secrets into chat, source files or GitHub issues.
The keys go only in Settings → Secrets and variables → Actions.
The existing Supabase Edge Function's stored PokéWallet key is **not
automatically available** to GitHub Actions. GitHub Pages never receives
either secret.

The importer stores resumable state privately in
`public.cv_admin_pokewallet_import_state` and individual provider IDs in
`public.cv_admin_pokewallet_catalog` (both RLS-enabled, no anonymous/client
access), then updates `public.cv_admin_job_progress` for the signed-in admin
dashboard. Changes are read-only with respect to live catalog search: import
and tentative image reconciliation do not publish automatic card artwork
overrides. Exact image matches are candidates only, and ambiguous matches
require review.

The first scheduled run can start only after both Actions secrets are
configured and the daily workflow exists on the default branch. Until then,
the dashboard correctly shows the import as not started.

## Administrator set-level image coverage

The admin dashboard now queries the read-only `public.cv_admin_set_coverage`
view, built with `security_invoker=true` so it respects source-table RLS.
It groups imported card records by **PokéWallet set ID**, counting imported
records, exact Kaggle matches, ambiguous matches and unmatched records.
This view derives counts from the existing catalog without changing the
daily importer or live card search.

`public.cv_admin_set_coverage_reviews` contains deliberate set-level
coverage determinations. The first administrator-confirmed exception is:

- **Delta Reign** (PokéWallet set ID `24831`): `confirmed_absent` in
  the Kaggle archive. Alternate licensed sources are **not yet checked**.

This is explicitly distinct from `unmatched_unverified`: a set with zero
matches may simply have different PokéWallet/Kaggle set folder names or
filename conventions. Confirmed gaps should be researched by set (for
example PokéWallet or Limitless artwork) rather than manually reviewing
each card. Candidate artwork and other unverified mappings are **never
automatically published** to the live marketplace.

The view and both underlying private tables are read-only for the
approved authenticated administrator, and no public browser role may
edit determinations. Changes to confirmed coverage evidence require
an explicitly reviewed privileged update. Imported-set counts represent
records processed so far, **not** verified set completion.
