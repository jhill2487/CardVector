# Putnam Collectibles Project Manual

Version: 1.0
Owner: Jared Hill
Project: Putnam Collectibles

---

# Mission

Build the best operating platform for trading card businesses.

Putnam Collectibles remains the production business. CardVector is the software
platform validated by that business.

The platform should automate repetitive work from image acquisition through
pricing, inventory, eBay export, fulfillment, and analytics while maximizing:

- Profit per hour
- Inventory turnover
- Listing quality
- Customer experience
- Scalability

The system should always prioritize reliability and maintainability over adding
unnecessary features.

---

# Long-Term Vision

CardVector Platform is composed of reusable applications and services.

```text
CardVector Platform
|
+-- CardVector Capture Studio
+-- CardVector Pricing Engine
+-- CardVector OS
+-- CardVector Mobile (future)
+-- CardVector Cloud (future)
```

## 1. CardVector Capture Studio

Purpose

- Acquire images
- Integrate with OBS Studio
- Support automatic and manual capture
- Manage front/back pairing
- Manage capture sessions
- Provide thumbnail review
- Prepare future Mobile and Binder Capture workflows

Capture Studio does not recognize cards. CardUploader currently performs card
recognition and listing generation.

## 2. CardVector OS

Purpose

Business operating system and workflow orchestrator.

Responsibilities

- Guided workflow
- Inventory
- Pricing handoff
- SKU management
- Batch management
- Location tracking
- Export management
- Reporting
- Analytics

Future

Inventory becomes the single source of truth.

## 3. CardVector Pricing Engine

Purpose

Price cards using explainable rules and marketplace intelligence.

Responsibilities

- Pricing strategy
- Market validation
- Rejection diagnostics
- Floor pricing
- Cart sweetener rules
- eBay CSV pricing support

## 4. CardUploader Integration

Purpose

External best-of-breed recognition and listing generation.

Responsibilities

- Card recognition
- Card metadata generation
- Listing source data
- Export files for CardVector OS import

## 5. Legacy Scanner Research

Purpose

Archived recognition and scanner research.

Responsibilities

- Historical OCR research
- Historical visual matching research
- Benchmark/reference material

Legacy Scanner Research is not the active production recognition path.

## 6. Pokemon Lookup Overlay

Purpose

Rapid lookup while buying, selling, streaming, and sorting cards.

Responsibilities

- Chrome Extension
- Local backend
- SQLite database
- Live pricing
- Fast search
- Whatnot support
- eBay support

Primary goal:

Instant pricing with minimal clicks.

## 7. Analytics

Eventually every business decision should become data driven.

Examples

- Sell-through
- Days to sell
- Average order value
- Average cards per order
- Profit by batch
- Profit by ETB
- Inventory aging
- Listing performance

---

# Current Development Phase

## Completed

- Capture Studio production validation
- CardUploader import workflow
- Pricing workflow
- eBay CSV generation and upload
- Inventory and location workflows
- Acquisition data during intake
- Legacy scanner research archive

## Current Priority

Build CardVector Platform v1.0.

Current focus

- CardVector Platform Rebrand
- Capture Studio v2
- CardVector Pricing Engine Marketplace Intelligence
- Workflow Polish
- Inventory Improvements

## Future

- Mobile Companion
- Inventory Transactions
- eBay Draft Automation
- TCGPlayer Sync
- AI-assisted grading support
- Warehouse management
- Business dashboard

---

# Project Architecture

```text
CardVector Capture Studio
|
v
CardUploader
|
v
CardVector OS
|
v
CardVector Pricing Engine
|
v
eBay CSV Export
|
v
Marketplace
```

Normalized Listing Pipeline

```text
CSV Input
|
v
Source Detection
|
v
Column Mapping / Adapter Profile
|
v
Normalized Listing
|
v
Existing Pricing Engine
|
v
Reports / Recommendations
|
v
Source-appropriate export
```

Overlay

```text
Pokemon Lookup Overlay
|
v
Local Backend
|
v
SQLite
|
v
Live Pricing
```

---

# Platform Principles

Every major subsystem should be reusable outside CardVector OS when practical.

Single Responsibility Principle:

- CardVector Capture Studio captures.
- CardVector Pricing Engine prices.
- CardVector OS orchestrates.
- CardUploader performs recognition.

Prefer modular components, reusable services, external best-of-breed
integrations, and workflow-first design.

---

# Development Standards

Every Codex session should:

1. Inspect the project before changing files.
2. Extend existing code whenever practical.
3. Avoid duplicate functionality.
4. Keep paths portable.
5. Avoid hard-coded user directories.
6. Preserve existing workflows.
7. Create backups before risky changes.
8. Bump versions when appropriate.
9. Run smoke tests.
10. Explain what changed.
11. Report any remaining issues.
12. Never silently delete data.

---

# Code Quality Standards

Prefer

- Small reusable modules
- Clear naming
- Comments around business logic
- Relative paths
- Configurable values

Avoid

- Giant scripts
- Duplicate logic
- Magic numbers
- Hard-coded paths

---

# Business Philosophy

The goal is NOT:

Maximum profit per listing.

The goal IS:

Maximum profit per hour.

Business decisions should optimize

- Inventory turnover
- Average order value
- Profit per shipment
- Cash flow
- Scalability

---

# Pricing Strategy

Current rules

Market <= 1.50

v

0.99

Market 1.51-2.99

v

1.49

Market 3.00-4.99

v

2.99

Market >=5.00

v

Keep market pricing

Never export below $0.99 unless explicitly requested.

---

# Shipping Strategy

Default

Buyer pays shipping.

Promotion

Free shipping on 3+ cards.

The export process must always confirm shipping settings before writing an eBay
CSV.

---

# Cart Sweetener Strategy

Cards at $0.99 are intentional cart builders.

Purpose

Increase

- Basket size
- Multi-card orders
- Revenue per shipment

Cart sweeteners should be tracked internally for analytics.

---

# Inventory Strategy

Simple first.

Location format

ETB-01-A

Use for

- Batch
- Custom SKU
- User SKU where appropriate
- Export logs

Avoid complex warehouse logic until necessary.

---

# eBay Export Workflow

Every export should perform:

1. Ask batch
2. Confirm shipping
3. Run pricing optimizer
4. Flag cart sweeteners
5. Display export summary
6. Require confirmation
7. Generate CSV
8. Write export log

Never modify required eBay columns.

---

# Capture Standards

Priority

Clean, paired, reviewable images first.

Preferred output

- Front image
- Back image
- Session metadata
- Capture count
- Pairing state
- CardUploader handoff readiness

Card recognition belongs to CardUploader unless a future milestone explicitly
changes the responsibility boundary.

---

# Overlay Standards

Primary purpose

Fast lookup.

Do not sacrifice speed for unnecessary features.

Pricing display priority

NM

v

LP

v

MP

v

HP/DMG

Variants should display without expanding.

---

# User Preferences

The project owner prefers

- Complete patch scripts
- Minimal manual editing
- Copy/paste commands
- One-step troubleshooting
- Plain-text Codex prompts

Provide pushback if an idea hurts

- Speed
- Accuracy
- Maintainability
- Business goals

Do not agree automatically.

---

# Versioning

Every meaningful feature should

- Update version
- Update changelog
- Preserve compatibility
- Include migration when necessary

---

# Changelog

## v1.0

Created unified project manual.

Established

- Vision
- Standards
- Architecture
- Roadmap
- Business rules
- Pricing philosophy
- Development workflow

This document becomes the authoritative reference for future development.

---

# Guiding Principle

When making development decisions, always ask:

"Does this make Putnam Collectibles faster, more accurate, easier to maintain,
and more profitable?"

If the answer is no, reconsider the approach.
