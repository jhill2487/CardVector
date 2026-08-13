# Putnam Collectibles

Putnam Collectibles is a unified trading card operations platform for managing
card intake, recognition, pricing, inventory locations, eBay exports, seller
operations, and business analytics.

# What Is The CardVector Platform?

CardVector Platform is the software ecosystem that powers Putnam Collectibles.

Unlike traditional software projects, the platform is developed while operating
the real business.

Every production work session generates operational feedback.

That feedback becomes improvements to the platform.

The platform exists to:

- reduce manual work
- improve listing velocity
- increase cash flow
- improve long-term profitability

Real business operations drive software development.

## Repository Layout

### Platform/

Software applications and reusable code.

Current application folders include:

- `Platform/Putnam_OS/`
- `Platform/Putnam_Scanner/`
- `Platform/Pokemon_Live_Price_Lookup/`
- `Platform/Putnam_Platform/`
- `Platform/TCG_Automation/`

CardVector OS support tools now live under:

- `Platform/Putnam_OS/Putnam_Listing_Optimizer/`
- `Platform/Putnam_OS/Putnam_Seller_Tools/`

### Business/

Daily business operations files.

Current business folders include:

- `Business/eBay_Store_Items/`
- `Business/Inventory/`

### Data/

Imports, exports, logs, media, processed files, databases, and generated data.

Current data folders include:

- `Data/Imports/`
- `Data/Exports/`
- `Data/Logs/`
- `Data/Media/`
- `Data/Processed/`
- `Data/Config/`

### Docs/

Project documentation and governance files.

Key files:

- `Docs/AGENTS.md`
- `Docs/PROJECT_STATUS.md`
- `Docs/CHANGELOG.md`
- `Docs/README.md`
- `Docs/PROJECT_MANUAL.md`
- `Docs/ROADMAP.md`
- `Docs/ROOT_REORGANIZATION_REPORT.md`
- `Docs/PATH_MANAGER.md`
- `Docs/GOVERNANCE.md`
- `Docs/GOVERNANCE_OVERVIEW.md`
- `Docs/PUTNAM_MANIFESTO.md`
- `Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`
- `Docs/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md`

### Tools/

Standalone helper tools and utilities.

The existing root `Tools/` folder remains in place because it is already the
target tool location.

### Archive/

Old versions, backups, and historical experiments.

### Work_Sessions/

Session logs, temporary work products, development notes, and agent/session
artifacts.

## Operational Rule

Daily listing and selling work should generally happen in `Business/` and
`Data/`.

Software development should generally happen in `Platform/`.

Project documentation should live in `Docs/`.

## Public Website Deployment

Website source is edited only in this private repository under `Docs/`.

The public `jhill2487/CardVector-site` repository is generated deployment output
for GitHub Pages and serves `cardvector.app`. Do not manually maintain duplicate
website source there.

Deployment is handled by `.github/workflows/pages.yml`, which exports an
allowlisted static artifact with `Tools/export_cardvector_site.py` and pushes it
to `CardVector-site` using the `CARDVECTOR_SITE_DEPLOY_TOKEN` repository secret.

Pokemon market briefs are edited as Markdown under
`Docs/content/market-briefs/`. The `market-brief-draft` GitHub issue template
stages ChatGPT-generated drafts with `content-draft` and `market-brief` labels.
Adding `ready-for-pr` runs `.github/workflows/market-brief-draft.yml`, which
turns the fenced Markdown article file into a draft PR. Merging that PR triggers
the normal public-site deployment.

Brief front matter may include optional affiliate links in the format
`Label|https://...`. Published brief pages render those links in a related-picks
panel with the marketplace affiliate disclosure. If a brief does not define a
custom link, the public page uses the configured Putnam Collectibles eBay
partner link from `Docs/site-config.json`.

Operational details live in `Docs/Reference/PUBLIC_SITE_DEPLOYMENT.md`.

## Platform Vision

The stable platform vision lives at `PLATFORM_VISION.md`.

Architecture lock effective 2026-07-01: CardVector product ownership is stable
and should be checked before feature work begins.

```text
CardVector Platform
|
+-- CardVector Capture Studio
+-- CardVector Pricing Engine
+-- CardVector OS
+-- CardVector Mobile (future)
+-- CardVector Cloud (future)
```

Putnam Collectibles remains the operating business. CardVector is the software
platform validated by that business.

CardUploader remains the external recognition and listing generation
integration. CardVector integrates with CardUploader rather than competing with
it.

## Applications

### CardVector OS

The business operating system for Putnam Collectibles.

Primary responsibilities:

- Inventory management
- Pricing engine
- SKU and location management
- eBay CSV export
- Listing optimization
- Export validation
- Business analytics
- Future marketplace automation

#### Current Production Workflow: v1.3.0

CardVector OS is the workflow conductor for:

```text
Capture -> CardUploader -> Processing -> eBay Upload
```

The production navigation is Home, Capture, Processing, Marketplace, Orders,
and Settings. Home contains only actionable Pending Work and source-labeled
Active Listings. Processing owns CardUploader CSV import, pricing review, and
the eBay export handoff.

CardVector does not replace CardUploader recognition, CardUploader managed
inventory, or eBay fulfillment.

#### Mobile Capture Queue

Retired as of 2026-08-13. Phone camera and camera-roll batch creation now belong
in CardUploader, which owns recognition, batch creation, managed inventory, and
eBay synchronization. CardVector.app `/capture`, `/mobile`, `/mobile-capture`,
ETB, and location routes display a retired-workflow message and direct the
operator to CardUploader batches.

CardVector OS no longer starts the automatic Mobile Capture queue watcher and no
longer opens the CardVector.app mobile capture website. The historical queue
code remains only for compatibility, migration review, and audit context until a
later cleanup phase explicitly removes it.

#### Production Workflow: v1.2.1

CardVector Platform v1.2.1 adds a shared OBS WebSocket connection manager for
Capture Studio so status checks, manual capture, and future capture features use
one connection path.

#### Production Workflow: v1.2.0

CardVector Platform v1.2.0 adds Capture Studio v2.1 Automated OBS Capture:

- Manual mode remains available.
- Auto mode uses live OBS frame comparison.
- Auto Capture waits for image stability before saving.
- Duplicate lockout and same-frame comparison prevent rapid repeated captures.
- Captures continue to use the existing front/back session pairing structure.
- Auto Capture settings live at
  `Platform/Putnam_OS/System/config/auto_capture_settings.json`.

#### Production Workflow: v1.1.1

CardVector Platform v1.1.1 is a production UI regression-fix release:

- Capture Studio uses `Capture` as the single production capture action.
- The Capture preview rail loads actual JPEG thumbnails when files are readable.
- Import owns CardUploader CSV intake.
- Pricing & Decisions focuses on analysis/export and does not duplicate the
  Import CSV drop zone.
- Inventory Label Center handles errors safely and logs label generation results.

#### Production Workflow: v1.1.0

CardVector Platform v1.1.0 focuses on daily operator speed:

- Capture Studio v2 uses one production action: `Capture Next Card`.
- OBS connection state is passive; `Retry` appears only when OBS is not
  connected.
- Recent capture pairs appear in a permanently docked right preview rail.
- Inventory Label Center v1 generates professional QR/PDF location labels under
  `Data/Exports/Labels/`.

The architecture remains locked:

- Capture Studio captures images.
- CardUploader recognizes cards.
- CardVector Pricing Engine handles pricing intelligence.
- CardVector OS orchestrates the business workflow.

### Legacy Scanner Research

Archived recognition and scanner research.

Primary responsibilities:

- Historical OCR and visual matching research
- Reference material for future recognition work
- No active production recognition responsibility

Card recognition responsibility has transitioned to CardUploader. CardVector
Capture Studio remains active for image acquisition.

### Pokemon Lookup Overlay

The lookup overlay and supporting backend.

Primary responsibilities:

- Chrome extension
- Local backend
- Live Pokemon lookup
- Market pricing
- Future Whatnot and eBay support

## Getting Started

Before making project changes:

1. Open the repository root.
2. Read the root `AGENTS.md` stub.
3. Read the documentation files in `Docs/`.
4. Inspect the relevant application code.
5. Reuse existing modules wherever practical.
6. Make the smallest safe change.
7. Run a smoke test when practical.
8. Report files changed, tests performed, and known issues.

## Development Workflow

Every new Codex session should read these files before making changes:

1. `Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`
2. `Docs/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md`
3. `Docs/AGENTS.md`
4. `Docs/PROJECT_STATUS.md`
5. `Docs/ROADMAP.md`
6. `Docs/CHANGELOG.md`
7. `Docs/README.md`

Then Codex should inspect the relevant project files and create an implementation
plan before editing.

## Governance

The permanent governance hierarchy is explained in `Docs/GOVERNANCE.md`.
`Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md` is the highest governing document.

## Platform Path Manager

Platform Path Manager v1.0 lives at `Platform/putnam_paths.py`.

New application code should use this module for repository paths instead of
assuming old root-level folders such as `Imports`, `Exports`, `logs`, `Media`,
or `processed` still exist. Those data locations now resolve under `Data/`.

## Documentation Files

### AGENTS.md

Permanent engineering handbook.

Defines how the project should be developed, including engineering philosophy,
business rules, coding standards, and Codex workflow expectations.

This file should almost never change.

### PROJECT_STATUS.md

Current project state.

Tracks current versions, priorities, repository structure, active milestones,
and known business rules.

This file can change frequently.

### CHANGELOG.md

Repository-level change history.

Tracks major application releases and governance-level changes. Future release
entries should use:

- Added
- Changed
- Fixed
- Known Issues

## Development Standard

Putnam Collectibles should favor maintainability, reliability, and business
impact over unnecessary features.

If a requested change does not reduce manual work, increase inventory turnover,
increase profit, reduce mistakes, improve customer experience, improve
maintainability, or produce useful analytics, challenge whether it belongs in
the project before implementing it.
