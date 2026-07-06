# Putnam Collectibles Development Standards

## Governance Hierarchy

Before beginning any work, read documentation in this order:

1. `Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`
2. `PLATFORM_VISION.md`
3. `Docs/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md`
4. `Docs/AGENTS.md`
5. `Docs/PROJECT_STATUS.md`
6. `Docs/ROADMAP.md`
7. `Docs/CHANGELOG.md`
8. `Docs/README.md`

Then inspect the relevant code.

If guidance conflicts, follow the highest-level governing document.

This handbook implements the CardVector Platform Standards, which implement the
Putnam Principles.

## Project Vision

Putnam Collectibles is the production trading card business.

CardVector is the software platform.

The product family is:

- CardVector Capture Studio: image acquisition.
- CardVector Pricing Engine: pricing, market validation, and listing recommendations.
- CardVector OS: workflow, inventory, analytics, and business operations.
- CardVector Mobile: future field companion.
- CardVector Cloud: future synchronization and web services.
- CardUploader: external recognition and listing generation integration.

CardVector integrates with CardUploader rather than competing with it.

## Architecture Lock

Effective 2026-07-01, every proposed feature should answer:

1. Which CardVector product owns this?
2. Can it be implemented without duplicating another module's responsibility?
3. Does it strengthen the platform or blur responsibilities?

If the answer to question 2 is "it duplicates another module," redesign before
implementing.

### CardVector OS

Purpose:

- Workflow orchestration
- Inventory
- Analytics
- Business operations
- SKU and location management
- eBay CSV handoff

### Legacy Scanner Research

Purpose:

- OCR
- Card Recognition
- Visual Matching
- Historical scanner research

Legacy Scanner Research is archived. CardUploader is the active recognition and
listing generation integration.

### Pokemon Lookup Overlay

Purpose:

- Chrome Extension
- Local Backend
- Live Pokemon Lookup
- Market Pricing
- Future Whatnot Integration

## Engineering Philosophy

Always inspect existing code before modifying it.

Prefer extending existing modules instead of creating duplicate functionality.

Keep code modular.

Keep code readable.

Keep business logic centralized.

Avoid unnecessary complexity.

Protect backwards compatibility whenever practical.

## Project Goals

Every feature should improve one or more of:

- Reduce manual work
- Increase inventory turnover
- Increase profit
- Increase average order value
- Reduce listing mistakes
- Improve customer experience
- Improve maintainability
- Produce useful business analytics

If a requested feature does not support these goals, challenge whether it
belongs before implementing it.

Before proposing a new feature, evaluate it against the Decision Filter defined
in `Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`.

If the feature does not clearly improve the business, explain why before
implementing it.

Constructive pushback is encouraged.

# BUSINESS PHILOSOPHY

## Cash Flow First

The primary purpose of CardVector OS is to help Putnam Collectibles generate cash
flow.

Software development must never significantly interrupt the business of:

- acquiring inventory
- listing inventory
- selling inventory
- shipping orders
- serving customers

When choosing between:

- building a perfect feature

or

- maintaining listing velocity

always prefer maintaining listing velocity.

The business never waits for the software.

The software waits for the business.

## Business Driven Development

Putnam Collectibles is the real-world production environment.

CardVector is developed to remove operational bottlenecks discovered while
running the business.

The business identifies problems.

CardVector solves them.

Avoid building features based solely on assumptions.

Favor solutions backed by real operational experience.

## Operational Feedback Loop

Every meaningful operational pain point should follow this cycle:

```text
Operate Business

Identify Bottleneck

Measure Time or Cost

Design Improvement

Implement in CardVector

Deploy

Measure Improvement

Repeat
```

This feedback loop should drive future development priorities.

## Deployment Philosophy

Every new feature should be classified before it becomes part of the daily
workflow.

### Production

Safe for everyday business use.

### Shadow Mode

Runs alongside the existing workflow for validation but does not replace it.

### Experimental

Proof-of-concept or early development.

Experimental features should never interrupt the normal business workflow.

# FEATURE LIFECYCLE

Every major feature in the Putnam Collectibles repository shall have one of the
following statuses.

## 🟢 Production

Definition:

Safe for daily operation of Putnam Collectibles.

Requirements:

- Successfully tested.
- Used in real production workflows.
- Trusted for daily business.

Production features may become the default workflow.

## 🟡 Shadow Mode

Definition:

Runs alongside the production workflow.

Purpose:

Collect real-world data without affecting business operations.

Examples:

- Suggested pricing
- Suggested titles
- Suggested inventory locations
- Suggested analytics

Shadow Mode features never replace the production workflow until promoted.

## 🟠 Experimental

Definition:

Research, prototype, or proof of concept.

Experimental features are not part of the normal business workflow.

They may be incomplete.

They may change frequently.

They should never interrupt daily listing, shipping, or inventory processing.

## 🔵 Planned

Definition:

Approved future work.

The feature has been accepted into the roadmap but development has not started.

## ⚪ Deferred

Definition:

Feature intentionally postponed.

Reasons may include:

- Low business value
- High complexity
- Waiting for operational feedback

Deferred does not mean cancelled.

## Feature Promotion Rules

### Experimental To Shadow Mode

Requirements:

- Successful internal testing.
- No major defects.

### Shadow Mode To Production

Requirements:

- Successfully used in the real Putnam Collectibles business.
- No significant operational issues.
- Improves one or more business metrics.

### Production To Deprecated

Only when replaced by a better workflow.

Maintain documentation until migration is complete.

## Permanent Business Rule

Business operations always take priority over software experimentation.

Production workflows should remain stable.

New features should mature through:

```text
Experimental

Shadow Mode

Production
```

without slowing listing velocity or reducing cash flow.

## General Coding Standards

Use portable paths.

Avoid hardcoded user directories.

Comment business logic.

Prefer reusable functions.

Never silently delete:

- Databases
- Logs
- Images
- Exports
- Inventory

Create backups before major refactors.

Run smoke tests whenever practical.

Always report:

- Files changed
- Tests performed
- Known issues

## Script And Tool Delivery

Every delivered script or tool should document:

- save location
- run command
- dependencies
- inputs
- outputs
- version or checkpoint when applicable
- changelog or change summary when applicable

## Versioning And Checkpoints

Every meaningful application update should include a clear version number or
checkpoint, changelog entry, and upgrade notes when user action is required.

Documentation-only governance updates do not change application versions unless
the project explicitly requires a documentation checkpoint.

## Decision Records

Major projects should maintain decision records when choices affect long-term
architecture, business workflow, or future maintenance.

Use a local `docs/DECISIONS.md` or an equivalent project decision log when a
project has its own documentation folder.

## CardVector OS Business Rules

Current philosophy:

Maximize:

- Profit
- Inventory Turnover
- Profit per Hour
- Profit per Envelope

Buyer Pays Shipping.

Promotion:

Free Shipping on 3+ Cards.

Current pricing rules:

- Market <= 1.50: Export Price = 0.99
- Market 1.51-2.99: Export Price = 1.49
- Market 3.00-4.99: Export Price = 2.99
- Market >= 5.00: Keep Market Price

Never export below:

```text
0.99
```

Cards at $0.99 are Cart Sweeteners.

Preferred inventory location format:

```text
ETB-01-A
```

Do not overbuild warehouse logic until requested.

## Scanner Standards

Accuracy before speed.

Never rename user photos unless requested.

Prefer benchmark testing.

Condition grading remains paused.

## Lookup Overlay Standards

Fast lookup first.

Keep UI simple.

Pricing priority:

1. NM
2. LP
3. MP
4. HP/DMG

Variant prices should be visible without expanding.

Version only the application being modified.

## User Preferences

Provide:

- Complete patch scripts
- Complete install scripts
- Minimal manual editing
- One-step troubleshooting
- Plain text instructions

Provide constructive pushback whenever a requested feature hurts:

- Speed
- Accuracy
- Maintainability
- Profitability

## Standard Codex Workflow

Before beginning any coding task:

1. Read the governance documents in the order listed above.
2. Inspect the project.
3. Create a plan.
4. Implement.
5. Test.
6. Report results.
