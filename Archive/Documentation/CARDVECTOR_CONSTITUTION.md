# CardVector Constitution

Version: 1.0

## 1. Mission

CardVector is a production workflow platform for trading card businesses.

Its purpose is to make trading card operations faster, clearer, more reliable,
and more profitable while preserving the operator judgment that makes the
business valuable.

CardVector exists to support real work:

- acquiring inventory
- capturing card images
- preparing listings
- pricing intelligently
- managing inventory
- fulfilling orders
- measuring business performance
- improving operational decisions

CardVector should become a durable operating system for trading card businesses,
not a collection of disconnected tools.

## 2. Core Philosophy

Build workflow, not novelty.

Every feature should improve the way work is performed. Interesting technology
is not enough. A feature earns its place by reducing friction, improving
accuracy, saving operator time, increasing cash flow, or improving decision
quality.

Buy commodity capabilities.

If a reliable external product already performs a commodity function well,
CardVector should integrate with it instead of rebuilding it without a clear
business advantage.

Build competitive advantages.

CardVector should focus engineering effort on the workflows, intelligence,
automation, and operational feedback loops that make a trading card business
faster and smarter over time.

Optimize operator time.

The most valuable resource is the operator's focused attention. CardVector
should remove repetitive work, reduce unnecessary decisions, and guide the
operator toward the next useful action.

Measure production value.

Production value is measured by business outcomes: time saved, cards processed,
listing velocity, error reduction, cash generated, inventory turnover, and
quality of operational decisions.

Keep business logic simple.

Business rules should be understandable, testable, and easy to explain. Complex
logic should exist only when it solves a proven operational problem.

## 3. Architecture Principles

One responsibility.

Every major product, module, service, and document should have a clear purpose.
If responsibility is unclear, clarify ownership before expanding the system.

One canonical owner.

Every shared capability should have one authoritative implementation. Duplicate
engines, services, registries, path systems, and workflows create confusion and
future risk.

One canonical folder.

Each project purpose should have a clear folder owner. New folders should not be
created when an existing canonical location can be extended.

One canonical document.

Every document should answer one question. When information belongs elsewhere,
link to the source of truth instead of copying it.

Shared services before duplicate code.

When multiple modules need the same capability, build or extend a shared service
instead of creating parallel implementations.

Configuration over hard-coded values.

Business settings, paths, thresholds, external service details, and operator
preferences should live in configuration or shared path services whenever
practical.

Portable paths.

CardVector must not depend on a specific username, drive, computer, or OneDrive
layout. Repository and data paths should be resolved through the platform path
system.

## 4. Development Rules

Extend before creating.

Before adding a module, script, folder, or workflow, search for the existing
owner and extend it when practical.

Never duplicate modules.

If a capability already exists, improve the canonical implementation instead of
creating a competing one.

Never duplicate folders.

Do not create a new folder for a purpose that already has a canonical location.

Never create nested folders unnecessarily.

Folder structure should make the project easier to navigate. Depth must be
earned by a real organizational need.

Always search before creating.

Every meaningful addition should begin with inspection of the current codebase,
documentation, and folder structure.

Prefer composition over replacement.

Improve systems by adding focused services, adapters, and integrations around
stable workflows. Replace a production workflow only when the replacement has
been validated and the migration path is clear.

Preserve production workflows.

Daily business operations take priority over architectural elegance. A working
workflow should not be disrupted for a cleaner design unless the transition is
safe, tested, and reversible.

Small incremental changes.

Prefer small, reviewable changes with clear validation over broad rewrites.

## 5. Cleanup Rules

Archive before delete.

Historical work may contain useful context. Deletion should be rare, explicit,
and preceded by backup or archive.

One cleanup package per commit.

Cleanup should be grouped into small packages with one purpose, one risk level,
and one validation path.

Validate after every package.

Every cleanup package should be followed by the smallest practical validation
that proves production workflows still work.

Never mix cleanup and feature work.

Cleanup changes and feature changes should be separate so rollback is simple
and responsibility is clear.

## 6. Production Validation Rules

Every production change requires validation.

Validation should match the risk of the change. Documentation changes may need
review only. Workflow changes need smoke tests. Changes touching exports,
pricing, capture, inventory, or orders need stronger validation.

Never trust compilation alone.

Compilation proves syntax. It does not prove workflow behavior, operator
experience, path correctness, data safety, or business readiness.

Production workflows take precedence over elegance.

When the ideal design conflicts with the current ability to list, sell, ship,
and serve customers, preserve the business workflow first and improve the design
incrementally.

## 7. Documentation Rules

Every document answers exactly one question.

If a document tries to answer several unrelated questions, split responsibility
by linking to canonical documents rather than duplicating content.

Cross-link instead of duplicate.

Repeated text becomes stale. The repository should point readers to the source
of truth.

Documentation is part of the product.

Good documentation protects workflow continuity, reduces repeated decisions,
and allows future contributors to understand why the system exists.

## 8. GitHub Rules

Small commits.

Each commit should have one purpose and be easy to review.

Descriptive commits.

Commit messages should describe the intent of the change, not only the files
edited.

Rollback must always be possible.

A change is not safe if it cannot be reversed. Commits should preserve a clear
path back to the previous working state.

## 9. Codex Rules

Codex must inspect before modifying.

Every session should read the governing documents and inspect the relevant
project area before making changes.

Codex must extend before creating.

Codex should search for existing owners and improve them rather than creating
new modules, folders, or scripts by default.

Codex must preserve canonical ownership.

CardVector responsibilities are intentional. Codex must avoid moving logic into
the wrong product or duplicating another module's role.

Codex must explain uncertainty instead of guessing.

When ownership, risk, or intent is unclear, Codex should state the uncertainty,
preserve existing behavior, and ask for review or document the open question.

## 10. Future Vision

CardVector is intended to become a modular operating system for trading card
businesses.

The platform should support:

- marketplace support
- capture hardware independence
- inventory intelligence
- workflow orchestration
- operator guidance
- marketplace synchronization
- analytics
- business intelligence

The long-term goal is a system where each module owns one responsibility, each
workflow is repeatable, each business decision becomes more informed over time,
and the operator can scale without losing control of quality.

