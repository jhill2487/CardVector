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

## Market Brief Draft Automation

Weekly Pokemon market briefs are source-controlled Markdown files under:

```text
Docs/content/market-briefs/
```

The issue template `.github/ISSUE_TEMPLATE/market_brief_draft.yml` provides a
reviewable draft intake form for ChatGPT-generated Monday briefs. Draft issues
should start with the labels `content-draft` and `monday-brief`.

The workflow `.github/workflows/market-brief-draft.yml` runs when either:

- an issue receives the `ready-for-pr` label
- the workflow is run manually with an issue number

The workflow:

1. Reads the issue title and complete fenced Markdown article file.
2. Creates one Markdown file in `Docs/content/market-briefs/`.
3. Validates the public site export.
4. Opens a draft pull request against `main`.
5. Comments on the issue with the draft PR link.

The importer intentionally rejects raw article text that is not inside a fenced
`markdown` code block. This prevents placeholder issue text, fact-check notes,
or TikTok package content from being accidentally published as the website
article.

The brief does not publish from the issue alone. It publishes only after the
draft PR is reviewed and merged, which then triggers the normal
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
template. Use labels content-draft and monday-brief. Include Filename, Fact-check
notes, TikTok package, and the complete article as a fenced markdown code block
under Article file. Do not add ready-for-pr until the draft has been reviewed.
```

## Public Artifact Allowlist

The exporter publishes only:

- `index.html`
- `404.html`
- `app.js`
- `style.css`
- `mobile-capture-config.js`
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

Do not use this token in browser code. Do not store it in `Docs/mobile-capture-config.js`.

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
- `app.js` contains `Capture Inventory`.
- `https://cardvector.app/mobile-capture-config.js` returns HTTP 200.
- `/etb/ETB-001` and `/location/ETB-001/A` resolve through the 404 fallback.
- `/location/ETB-001/A` shows the Mobile Capture UI.
- With placeholder Supabase config, the UI appears and reports that the backend is not configured.
- `deployment-manifest.json` contains the source CardVector commit SHA.
- No service-role key or private file paths are present in static files.

## Troubleshooting

- Missing `CARDVECTOR_SITE_DEPLOY_TOKEN`: add the repository secret in `CardVector`.
- No generated commit: the exported artifact matches `CardVector-site`.
- Missing Mobile Capture UI: check `app.js`, `mobile-capture-config.js`, and `deployment-manifest.json` on `cardvector.app`.
- QR route shows the homepage only: verify `404.html` deployed and Pages still serves from `CardVector-site` root.
