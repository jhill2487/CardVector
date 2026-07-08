# Putnam Collectibles

Putnam Collectibles is a unified trading card operations platform for managing
card intake, recognition, pricing, inventory locations, eBay exports, seller
operations, and business analytics.

# What Is The Putnam Platform?

The Putnam Platform is the software ecosystem that powers Putnam Collectibles.

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

Putnam OS support tools now live under:

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

## Applications

### Putnam OS

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

### Putnam Scanner

The card recognition and intake system.

Primary responsibilities:

- OCR
- Card recognition
- Visual matching
- Image processing
- Inventory intake
- Future inventory automation

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
