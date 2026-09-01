# CV-ADR-026 - Pause Supabase Location Registry Migration And Retire CardVector Operating Workflows

## Status

Accepted.

## Date

2026-09-01

## Owner

Project owner.

## Context

Earlier CardVector architecture phases assumed CardVector would continue to
operate capture, location registry, batch workflow, and pricing review
workflows while delegating recognition and managed inventory to CardUploader.
That led to a Supabase capture/location registry migration intended to replace
the legacy desktop-local ETB JSON registry.

The project owner has now confirmed that active operations no longer use
CardVector for capture, listing, or pricing exercises. CardUploader now handles
camera-roll/capture intake, recognition, standardized listing creation, managed
inventory, and automatic eBay synchronization. The practical near-term
CardVector direction is the CardUploader browser/helper workflow, public
CardVector.app content/storefront work, and optional read-only analysis.

## Problem

Continuing to treat the Supabase capture/location registry migration as the next
active migration path would create unnecessary repository churn and operational
risk. It would also keep CardVector pointed at workflows the owner is no longer
using.

At the same time, the prior migration artifacts are valuable evidence and
should not be deleted or overwritten. The CardUploader helper work remains
active and should not be retired as part of this decision.

## Evidence

- The project owner stated on 2026-09-01 that CardVector is no longer used for
  capture, listing, or pricing exercises.
- CardUploader provides the active capture, recognition, managed inventory,
  standardized listing, and automatic eBay synchronization workflow.
- The Supabase capture/location registry migration was never cut over as the
  production source of truth for active operations.
- Existing migration reports identified conflicts and dry-run gates, but no
  production data import or final cutover is required for the current workflow.
- The CardUploader browser/helper direction is still useful for working with
  the actual CardUploader automatic inventory page.

## Decision

Pause and archive the Supabase capture/location registry migration as a
historical/restartable workstream. It is no longer the active next migration
path.

Retire CardVector-owned capture, listing, and pricing operating workflows from
the active roadmap unless a future ADR reauthorizes them with a current operator
need.

Keep CardUploader browser/helper automation as an active CardVector workstream
because it supports the owner's real workflow without making CardVector a
competing inventory, listing, or capture authority.

## Alternatives Considered

- Continue the Supabase capture/location registry cutover.
- Delete the Supabase migration artifacts immediately.
- Keep CardVector OS capture/listing/pricing workflows active until a full web
  replacement exists.
- Move all inventory and listing ownership into CardVector.

## Consequences

- Do not run production Supabase capture/location registry migrations or legacy
  registry imports without a new explicit approval.
- Supabase migration files and reports may remain as historical evidence,
  rollback context, and restart material.
- CardVector.app should not advertise retired capture/location registry
  workflows as active operator tools.
- CardVector OS remains a legacy/admin surface, not the active operating system.
- CardUploader remains the active operational owner for capture, recognition,
  managed inventory, listing creation, and automatic eBay synchronization.
- CardVector helper work should integrate with the CardUploader workflow rather
  than invent a parallel source of truth.

## Dependency Impact

No runtime dependency changes are authorized by this ADR. Future helper code may
interact with CardUploader browser pages through explicit operator-approved
automation boundaries, but it must not create a competing inventory or listing
database.

## Migration Impact

The active migration path shifts away from Supabase capture/location registry
cutover and toward:

1. CardUploader browser/helper hardening.
2. CardVector.app public content and storefront improvements.
3. Read-only business analysis where useful.
4. Future integrations only when they support the actual CardUploader/eBay
   workflow.

## Compatibility Impact

Existing CardVector OS and Supabase registry code may remain for compatibility,
audit, or historical reference until a controlled cleanup phase removes or
archives it. No launcher, database table, or production data is changed by this
decision.

## Testing Requirements

This ADR is documentation-only. Future cleanup phases must verify that no active
operator workflow depends on retired CardVector capture, listing, or pricing
surfaces before removing code.

## Rollback Plan

Revert this ADR and the corresponding manifest, decision-log, ownership, and
roadmap documentation updates. A future owner-approved ADR may also reactivate
the Supabase capture/location registry migration.

## Approval

Approved by the project owner in conversation on 2026-09-01.

## Supersedes

The active-roadmap portion of CV-ADR-024 and CV-ADR-025 that treated Supabase
capture/location registry cutover and CardVector-hosted capture/listing/pricing
workflows as near-term operator priorities.

## Superseded By

None.
