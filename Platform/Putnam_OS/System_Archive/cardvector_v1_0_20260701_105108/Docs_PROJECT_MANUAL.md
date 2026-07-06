# Putnam Collectibles Project Manual

Version: 1.0
Owner: Jared Hill
Project: Putnam Collectibles

---

# Mission

Build the best end-to-end trading card operations platform for a small-to-medium card business.

The platform should automate every repetitive task from scanning a card to shipping an order while maximizing:

- Profit per hour
- Inventory turnover
- Listing quality
- Customer experience
- Scalability

The system should always prioritize reliability and maintainability over adding unnecessary features.

---

# Long-Term Vision

Putnam Collectibles is composed of four major systems.

## 1. Putnam Scanner

Purpose

- Card recognition
- OCR
- Visual matching
- Image processing
- Card intake

Future

Scan Card

↓

Identify Card

↓

Populate Inventory

↓

Create Listing

---

## 2. Putnam OS

Purpose

Business operating system.

Responsibilities

- Inventory
- Pricing
- SKU management
- Batch management
- Location tracking
- Export management
- Reporting
- Analytics

Future

Inventory becomes the single source of truth.

---

## 3. Pokémon Lookup Overlay

Purpose

Rapid lookup while buying, selling, streaming and sorting cards.

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

---

## 4. Analytics

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

✓ Scanner foundation

✓ OCR integration

✓ Kaggle image database

✓ SQLite database

✓ Chrome extension

✓ Viewer backend

✓ eBay CSV generation

---

## Current Priority

Build Putnam OS

Current focus

- Listing Optimizer
- Batch Manager
- Pricing Engine
- Inventory Workflow
- Export Validation

---

## Future

- eBay Draft Automation
- TCGPlayer Sync
- Multi-card Scanner
- Mobile Scanner
- AI-assisted grading
- Warehouse management
- Business dashboard

---

# Project Architecture

Scanner

↓

Inventory Database

↓

Putnam OS

↓

Pricing Engine

↓

eBay Export

↓

Marketplace

Overlay

↓

Local Backend

↓

SQLite

↓

Live Pricing

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

↓

0.99

Market 1.51–2.99

↓

1.49

Market 3.00–4.99

↓

2.99

Market >=5.00

↓

Keep market pricing

Never export below $0.99 unless explicitly requested.

---

# Shipping Strategy

Default

Buyer pays shipping.

Promotion

Free shipping on 3+ cards.

The export process must always confirm shipping settings before writing an eBay CSV.

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
- User SKU (where appropriate)
- Export logs

Avoid complex warehouse logic until necessary.

---

# eBay Export Workflow

Every export should perform:

1.
Ask batch

↓

2.
Confirm shipping

↓

3.
Run pricing optimizer

↓

4.
Flag cart sweeteners

↓

5.
Display export summary

↓

6.
Require confirmation

↓

7.
Generate CSV

↓

8.
Write export log

Never modify required eBay columns.

---

# Scanner Standards

Priority

Recognition accuracy first.

Inventory automation second.

Preferred output

Card Name

Set

Card Number

Confidence

Status

Benchmark images should be used whenever OCR or crop logic changes.

Condition grading is intentionally postponed.

---

# Overlay Standards

Primary purpose

Fast lookup.

Do not sacrifice speed for unnecessary features.

Pricing display priority

NM

↓

LP

↓

MP

↓

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

"Does this make Putnam Collectibles faster, more accurate, easier to maintain, and more profitable?"

If the answer is no, reconsider the approach.
