# CV-ADR-025 - CardVector.app Is The Primary Future Operator UI

## Status

Accepted.

## Date

2026-07-30

## Owner

Project owner.

## Context

Earlier architecture phases assumed CardVector OS would remain the primary
operator shell while CardVector.app provided public storefront and mobile
capture workflows. That assumption was mostly driven by workstation-local
Scanner and OBS workflows.

The project owner has now confirmed Scanner and OBS workflows are obsolete for
the current operating model. Current active work increasingly depends on shared
Supabase-backed state, CardUploader batch/history references, mobile capture,
ETB/location visibility, price review, and future existing-listing review.

## Problem

Keeping CardVector OS as the long-term primary UI would preserve workstation
dependency and keep new workflows split between desktop-local state and the web
application. CardVector needs one primary operator interface that is usable away
from the workstation while still preserving legacy/admin desktop tools during
transition.

## Evidence

- `Docs/Architecture/README.md` already records Supabase as the accepted
  canonical source for shared capture batches, ETBs/storage locations, capture
  images, and their relationships.
- `Docs/Architecture/CardVector_Architecture_Manifest.md` records CardUploader
  as the managed-inventory owner and Marketplace Intelligence as pricing owner.
- The project owner confirmed on 2026-07-30 that Scanner/OBS workflows have
  become obsolete.
- CardVector.app already hosts mobile capture and authenticated Supabase-backed
  workflows.
- CardVector OS remains the current production launcher target and contains
  legacy/admin workflow surface area that must not be removed without caller and
  behavior accounting.

## Decision

CardVector.app becomes the primary future operator UI for CardVector.

CardVector OS becomes a temporary compatibility/admin desktop tool during
migration. It remains supported until its active workflows are moved, delegated,
or explicitly retired.

Scanner and OBS workflows are no longer part of the active product roadmap for
the current operator workflow. Their source may remain for historical reference
or compatibility until a dedicated retirement phase safely archives or removes
it.

## Alternatives Considered

- Keep CardVector OS as the permanent primary UI.
- Rewrite CardVector OS immediately as a web application.
- Delete Scanner/OBS code immediately.
- Maintain independent desktop and web implementations indefinitely.

## Consequences

- New user-facing workflow UI should default to CardVector.app unless it has a
  proven workstation-only requirement.
- CardVector OS may continue to expose legacy/admin tools but must not become
  the place for new primary workflow UX.
- Shared workflow state should use Supabase, CardUploader, eBay, Marketplace
  Intelligence, and application-layer services rather than desktop-local JSON as
  the primary source.
- The public/static deployment boundary must be preserved: private source,
  secrets, runtime data, and service-role credentials must not enter public
  assets.
- Existing desktop launchers and `putnam_os.py` remain unchanged by this
  decision.

## Dependency Impact

CardVector.app presentation may call shared application/integration APIs and
Supabase-authenticated workflows. Domain logic, pricing, inventory ownership,
and persistence ownership do not move into frontend markup.

CardVector OS compatibility surfaces must delegate to canonical owners when
migrated.

## Migration Impact

Future phases should prioritize moving these UI surfaces to CardVector.app:

1. Supabase ETB/location registry and freshness state.
2. Mobile capture batch status and capture-session review.
3. Batch workflow dashboard.
4. Price review and pricing explanation.
5. Existing listing review readiness.
6. Inventory/search dashboards over CardUploader/eBay truth.

Scanner/OBS retirement should be handled as a later cleanup phase after all
callers, launchers, tests, and operator references are inventoried.

## Compatibility Impact

CardVector OS remains a compatibility/admin surface. No public desktop method,
launcher, or file path is removed by this ADR.

## Testing Requirements

Every migrated workflow must retain:

- desktop compatibility tests where the old UI still delegates,
- CardVector.app contract tests,
- Supabase auth/RLS tests where state is shared,
- no-secret public export checks,
- mobile viewport checks when the workflow is mobile-relevant.

## Rollback Plan

Revert this ADR and the matching manifest/ownership/roadmap documentation
updates. No production code or data changes are required for rollback because
this decision does not change runtime behavior.

## Approval

Approved by the project owner in conversation on 2026-07-30.

## Supersedes

The earlier target assumption that `cardvector.presentation.desktop` is the
long-term primary presentation shell.

## Superseded By

None.
