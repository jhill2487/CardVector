# Public Site Deployment

Status: Reference

Date: 2026-07-13

## Repository Roles

`jhill2487/CardVector` is the private authoritative source repository. Website source changes belong under `Docs/`.

`jhill2487/CardVector-site` is the public deployment repository for `cardvector.app`. It is generated from `CardVector/Docs` and should not be edited manually.

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
