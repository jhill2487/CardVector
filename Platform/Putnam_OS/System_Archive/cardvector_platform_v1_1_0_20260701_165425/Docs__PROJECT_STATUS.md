# Putnam Collectibles Project Status

## Purpose

`PROJECT_STATUS.md` tracks the current state of development.

This file will change frequently.

## Governance

Project governance follows the hierarchy defined in
`Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`.

## Current Versions

### CardVector OS

v1.0.0

### CardVector Platform

v1.0

### Legacy Scanner Research

Archived

### Pokemon Lookup Overlay

Independent Version

### Marketplace Intelligence

v1.2.0

## Repository Layout

The root folder is organized for business operations first and software
development second.

### Platform/

Software applications and reusable code.

Primary application folders:

- `Platform/Putnam_OS/`
- `Platform/Putnam_Scanner/`
- `Platform/Pokemon_Live_Price_Lookup/`
- `Platform/Putnam_Platform/`
- `Platform/TCG_Automation/`

CardVector OS support tools:

- `Platform/Putnam_OS/Putnam_Listing_Optimizer/`
- `Platform/Putnam_OS/Putnam_Seller_Tools/`

### Business/

Daily business operations files.

- `Business/eBay_Store_Items/`
- `Business/Inventory/`

### Data/

Imports, exports, logs, media, processed files, databases, and generated data.

- `Data/Imports/`
- `Data/Exports/`
- `Data/Logs/`
- `Data/Media/`
- `Data/Processed/`
- `Data/Config/`

### Docs/

Project documentation and governance files.

- `Docs/AGENTS.md`
- `Docs/PROJECT_STATUS.md`
- `Docs/CHANGELOG.md`
- `Docs/README.md`
- `Docs/PROJECT_MANUAL.md`

### Tools/

Standalone helper scripts and utilities.

### Archive/

Old versions, backups, and historical experiments.

### Work_Sessions/

Session logs, temporary work products, and development notes.

## Operational Rule

Daily listing and selling work should generally happen in `Business/` and
`Data/`.

Software development should generally happen in `Platform/`.

Project documentation should live in `Docs/`.

## Dual-Track Roadmap

### Track A: Putnam Collectibles Business

Purpose:

- Generate cash flow.
- Increase inventory turnover.
- Increase listing velocity.
- Increase average order value.
- Improve operational efficiency.
- Operate continuously regardless of CardVector OS development.

### Track B: CardVector Platform

Purpose:

- Observe the business.
- Identify bottlenecks.
- Automate repetitive work.
- Reduce manual effort.
- Increase profitability.
- Support business growth.

### Relationship

The business is the customer.

CardVector is the software platform.

Every CardVector feature should exist because it solves a real business problem
experienced while operating Putnam Collectibles.

## Current Priorities

### Priority 1

CardVector Platform Rebrand

### Priority 2

Capture Studio v2

### Priority 3

CardVector Pricing Engine Marketplace Intelligence

## Current CardVector OS Goals

- Inventory Automation
- Legacy Listing Optimizer (retired from active operator workflow)
- CardVector Pricing Engine
- Export Validation
- Business Analytics
- Inventory Locations
- Platform Path Manager v1.0
- Acquisition Data During Intake

## Known Business Rules

- Buyer Pays Shipping
- Free Shipping on 3+ Cards
- Cart Sweetener Pricing
- No fixed-price eBay export below $0.99
- Cart sweetener floor: $0.99
- Simple ETB Location System

## Feature Status

Features are organized using the permanent lifecycle system defined in
`Docs/AGENTS.md`.

### 🟢 Production

- eBay CSV Export
- Export Logging
- Buyer Pays Shipping policy
- Free Shipping on 3+ Cards promotion rule
- Simple ETB Location System
- Platform Path Manager v1.0

### Platform Path Rule

New code should use `Platform/putnam_paths.py` for repository-aware paths.
Do not assume `Imports`, `Exports`, `logs`, `Media`, or `processed` exist at
the repository root; use the `Data/` layout through the path manager.

### 🟡 Shadow Mode

- Legacy Listing Optimizer (archive/reference only)
- Dynamic Pricing
- SKU Repair Planner
- Inventory Audit Mode v2
- Sales Analytics

### 🟠 Experimental

- AI Pricing Assistant
- Marketplace Forecasting
- Marketplace Intelligence v1.0
- CardVector Capture Studio v2

### 🔵 Planned

- TCGplayer Integration
- Shopify Integration
- Mobile Companion App
- Full Inventory Analytics Dashboard
- End-to-end CardUploader to CardVector OS listing pipeline

### ⚪ Deferred

- Automated Condition Grading

Reason:

Deferred until the core listing and sales workflow is mature.

### Backlog / Planned

#### Profit Dashboard

Includes:

- profit per envelope
- revenue per envelope
- packaging cost
- USPS cost
- eBay fees
- net profit per order
- profit by shipping method
- profit by inventory location
- profit by card game
- fulfillment profile reporting

#### Bulk Sales Performance Report

Includes:

- Standard Envelope orders only
- exclude Ground Advantage when analyzing bulk strategy
- single-card vs multi-card orders
- average cards per envelope
- shipping paid vs free shipping
- cart sweetener attachment rate
- promoted vs organic
- revenue per envelope
- profit per envelope when available

#### Offer Analytics Dashboard

Includes:

- Best Offer usage
- accepted / declined / countered / expired
- offer activity by price tier
- average discount
- revenue impact
- whether Best Offer should be disabled under certain price thresholds

#### Promotion Performance Dashboard

Track current promotion experiment:

- Free shipping over $10
- $0.99 items only:
- 2 items = 5% off
- 3 items = 10% off
- 4+ items = 15% off

Metrics to eventually compare:

- cards per envelope
- average order value
- revenue per envelope
- profit per envelope
- percentage of orders over $10
- cart sweetener performance

### Backlog / Future

#### Module Completeness Pass

Goal:

All CardVector OS modules should have at least one useful working function.
No blank description-only modules.

## Feature Lifecycle Business Rule

Business operations always take priority over software experimentation.

Production workflows should remain stable.

New features should mature through:

```text
Experimental

Shadow Mode

Production
```

without slowing listing velocity or reducing cash flow.

## Roadmap Reference

Future direction belongs in `Docs/ROADMAP.md`.

`PROJECT_STATUS.md` tracks the current state of the project. `ROADMAP.md`
tracks planned future work.

## Success Metrics

Track the following over time:

- Cards listed per hour
- Orders per week
- Average cards per order
- Weekly cash generated
- Average days from acquisition to listing
- Average days from listing to sale

Every significant CardVector OS feature should improve one or more of these metrics.

## Current Milestone

Transition CardVector OS from automation scripts into a complete business operating
system while keeping Putnam Collectibles operating continuously.
