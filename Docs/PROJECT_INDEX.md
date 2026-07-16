# PROJECT_INDEX.md

**Status:** Canonical

# Purpose

PROJECT_INDEX.md is the navigation document for the CardVector repository.

It identifies where authoritative information resides and establishes the recommended reading order for developers, AI assistants, and future contributors.

---

# Read Order

New contributors should review the repository in the following order:

1. PROJECT_MANUAL.md
2. PROJECT_ROADMAP.md
3. DEVELOPMENT_LOG.md
4. CHANGELOG.md
5. README.md

This order provides:

- Project philosophy
- Current direction
- Historical context
- Recent changes
- Repository overview

---

# Canonical Documents

The following documents define CardVector.

- PROJECT_MANUAL.md
- PROJECT_INDEX.md
- PROJECT_ROADMAP.md
- DEVELOPMENT_LOG.md
- CHANGELOG.md
- README.md

These documents are considered living documentation.

---

# Reference Documents

Reference documents provide detailed information for specific subsystems.

Examples include:

- Path management
- Fulfillment profiles
- Hardware setup
- API references
- Deployment notes

Current deployment reference:

- `Docs/Reference/PUBLIC_SITE_DEPLOYMENT.md`
- `Docs/Reference/MOBILE_CAPTURE_SUPABASE_SETUP.md`
- `Docs/Reference/MOBILE_CAPTURE_PIPELINE_AUDIT.md`

Current desktop queue implementation:

- `Platform/Putnam_OS/System/tools/mobile_capture_queue.py`
- CardVector OS workspace: `Capture`, with detailed `Capture Queue` available contextually

Current desktop workflow implementation:

- `Platform/Putnam_OS/System/app/workflow_context.py`
- CardVector OS workspaces: `Home`, `Capture`, `Processing`, `Marketplace`, `Orders`, `Settings`

Reference documents expand upon the canonical documents but do not define project architecture.

---

# Archive

Archived documents preserve historical decisions and prior planning.

Examples include:

- Previous roadmaps
- Governance documents
- Manifestos
- Migration reports
- Historical status reports

Archived documents are retained for historical value and should not be considered the current architectural source of truth.

---

# Repository Organization

The repository is organized into four categories:

• Source Code
• Documentation
• Operational Data
• Tools

Documentation is further organized as:

• Canonical
• Reference
• Archive

---

# AI Assistant Guidance

AI assistants should treat the repository as the authoritative memory of CardVector.

Recommended reading order:

1. PROJECT_MANUAL.md
2. PROJECT_ROADMAP.md
3. DEVELOPMENT_LOG.md

Reference documentation should be consulted only when additional subsystem detail is required.

Historical documents should not override the canonical documentation.

---

# Documentation Philosophy

CardVector intentionally maintains a small number of canonical documents.

Existing canonical documentation should be expanded before creating new top-level documents.

Reference material belongs in Docs/Reference.

Historical material belongs in Docs/Archive.

The objective is to preserve project knowledge while minimizing documentation sprawl.
