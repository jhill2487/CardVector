# Public Site Deployment

Status: Reference

Date: 2026-07-13

## Repository Roles

`jhill2487/CardVector` is the private authoritative source repository. Website source changes belong under `Docs/`.

`jhill2487/CardVector-site` is the public deployment repository for `cardvector.app`. It is generated from `CardVector/Docs` and should not be edited manually.

Public marketplace and inquiry destinations are maintained once in
`Docs/site-config.json`. The exporter resolves those values into direct HTML and
JavaScript links so the storefront remains navigable when JavaScript is unavailable.
Placeholder or non-HTTPS values stop the export.

## Deployment Flow

```text
CardVector/Docs
-> Tools/export_cardvector_site.py
-> CardVector-site
-> GitHub Pages
-> cardvector.app
```

The workflow is `.github/workflows/pages.yml` in `CardVector`.

It runs on:

- pushes to `main` affecting `Docs/**`
- changes to the deployment workflow
- changes to `Tools/export_cardvector_site.py`
- manual `workflow_dispatch`

## Market Brief Publishing Automation

Pokemon market briefs are source-controlled Markdown files under:

```text
Docs/content/market-briefs/
```

The issue template `.github/ISSUE_TEMPLATE/market_brief_draft.yml` provides a
reviewable draft intake form for ChatGPT-generated market briefs. Draft issues
should start with the labels `content-draft` and `market-brief`.

The workflow `.github/workflows/market-brief-draft.yml` runs when either:

- an issue receives the `approved-to-publish` label
- the workflow is run manually with an issue number

The workflow:

1. Reads the issue title and complete fenced Markdown article file.
2. Creates one Markdown file in `Docs/content/market-briefs/`.
3. Validates the public site export.
4. Opens a normal pull request against `main`.
5. Merges the PR after the issue approval and site-export validation.
6. Comments on the issue with the publish PR link.

The importer intentionally rejects raw article text that is not inside a fenced
`markdown` code block. This prevents placeholder issue text, fact-check notes,
or TikTok package content from being accidentally published as the website
article.

The issue approval is the human publishing gate. After the
`approved-to-publish` label is applied, the generated PR is mechanical: it
preserves the GitHub audit trail, then merges to trigger the normal
`.github/workflows/pages.yml` deployment to `CardVector-site`.

Fact-check notes and TikTok package content remain in the issue as staging
evidence. They are not copied into the public website article.

Market briefs may include affiliate calls to action through front matter:

```yaml
affiliateLinks:
  - "Shop Putnam Collectibles on eBay|https://www.ebay.com/str/jhilltcg?mkcid=1&mkrid=711-53200-19255-0&siteid=0&campid=5339178316&customid=&toolid=10001&mkevt=1"
```

The public page renders these links as a related-picks panel with the affiliate
disclosure. If no custom affiliate link is supplied, the brief page uses the
default eBay partner link configured in `Docs/site-config.json`.

Recommended recurring-task output:

```text
Create a GitHub issue in jhill2487/CardVector using the Market Brief Draft
template. Use labels content-draft and market-brief. Include Filename, Fact-check
notes, TikTok package, and the complete article as a fenced markdown code block
under Article file. Do not add approved-to-publish until the draft has been
reviewed and is ready to publish.
```

## Public Artifact Allowlist

The exporter publishes only:

- `index.html`
- `404.html`
- `app.js`
- `style.css`
- `CNAME`
- `_config.yml`
- `.nojekyll`
- `README.md`
- `deployment-manifest.json`
- `content/market-briefs/index.json`
- `assets/putnam-profile.png`
- `assets/putnam-profile-onepiece.png`
- `assets/putnam-ebay-banner.png`

It does not publish `Docs/Reference`, `Docs/Reports`, private desktop code, operational data, business exports, Python files, CSV files, or service-role secret references.

## Required GitHub Secret

Secret name in `jhill2487/CardVector`:

```text
CARDVECTOR_SITE_DEPLOY_TOKEN
```

Recommended token type:

- Fine-grained GitHub personal access token.
- Repository access limited to `jhill2487/CardVector-site`.
- Minimum repository permission: `Contents: Read and write`.

Do not grant access to other repositories unless operationally required.

Do not use this token in browser code.

## Rotation

1. Create a replacement fine-grained token with the same minimum scope.
2. Update `CARDVECTOR_SITE_DEPLOY_TOKEN` in `CardVector` repository secrets.
3. Run the deployment workflow manually.
4. Confirm the generated commit lands in `CardVector-site`.
5. Revoke the old token.

GitHub masks secret values in logs. The workflow never prints the token and passes it only to `actions/checkout`.

## Manual Deployment Procedure

Use this only for troubleshooting or first-time bootstrap:

```powershell
py Tools\export_cardvector_site.py --output C:\Users\JaredHill\OneDrive\CardVector-site --source-sha <CardVector commit>
```

Then review, commit, and push `CardVector-site`.

## Rollback

Rollback is an ordinary Git revert in `CardVector-site`:

```powershell
git revert <deployment_commit>
git push origin main
```

Long-term source fixes should still be made in `CardVector/Docs` and redeployed.

## Verification

After deployment:

- `https://cardvector.app/app.js` returns HTTP 200.
- `app.js` contains `Operator Dashboard`.
- `/etb/ETB-001` and `/location/ETB-001/A` resolve through the 404 fallback.
- `/capture`, `/mobile`, `/mobile-capture`, `/etb/ETB-001`, and `/location/ETB-001/A` show the retired mobile-capture message and direct operators to CardUploader batches.
- `deployment-manifest.json` contains the source CardVector commit SHA.
- No service-role key or private file paths are present in static files.

## Supabase Egress Controls

CardVector.app operator pages run in egress-safe mode by default. Registry,
batch, listing, and allocation views use metadata-only Supabase reads, capped
row limits, and a five-minute browser cache. Operator pages expose a manual
`Refresh from Supabase` action for cases where current cloud state is required.

Mobile capture is retired and no longer uploads original images from
CardVector.app. Public pages must not auto-download Supabase storage originals
for previews; use metadata, counts, thumbnails, or explicit operator-open
actions instead.

## Troubleshooting

- Missing `CARDVECTOR_SITE_DEPLOY_TOKEN`: add the repository secret in `CardVector`.
- No generated commit: the exported artifact matches `CardVector-site`.
- Capture route still opens a camera workflow: check `app.js` and `deployment-manifest.json` on `cardvector.app`.
- QR route shows the homepage only: verify `404.html` deployed and Pages still serves from `CardVector-site` root.
