# AI_ENGINEERING_CONTEXT

## Purpose
CardVector is the operating system for Putnam Collectibles.

### Core Principles
- Production reliability first.
- Optimize for measurable business value.
- Preserve established architecture.
- Keep solutions simple.

## Established Decisions
- ETBs have permanent IDs.
- Locations have permanent IDs.
- Cards do NOT receive unique inventory IDs.
- ETB + Location is the authoritative physical inventory reference.
- Acquisition tracking is optional metadata.

## Engineering Rules
- Validate before committing.
- Commit locally.
- Never push unless instructed.
- Never commit runtime/operational JSON files.
- Preserve USERENVIRONMENT portability.
- Flag architectural conflicts before implementing changes.
