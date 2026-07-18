# CV-ADR-021 - CardUploader Inventory Ownership

- **Decision ID:** CV-ADR-021
- **Status:** Accepted
- **Date:** 2026-07-18
- **Owner:** Project owner

## Context And Evidence

CardUploader supplies the managed inventory export consumed by CardVector. Its
records include product identity, external SKUs, quantity, status, price, and
location references. CardVector currently has a read-only snapshot, inventory
audit/reconciliation reports, and ETB/Supabase capture-location projections.
Repository search found no CardVector reservation, allocation, pick
confirmation, or authoritative inventory synchronization implementation.

## Decision

CardUploader is the canonical owner of inventory identity, quantity, available,
reserved and sold state, physical location, image association, allocation,
reservation, picking state, lifecycle, persistence, and synchronization.
CardVector owns presentation and orchestration over CardUploader contracts.

`Platform/cardvector/inventory` must not be created as a competing inventory
implementation. The approved integration surface is
`Platform/cardvector/integrations/carduploader`, consumed through
`Platform/cardvector/application`.

## Alternatives Considered

1. Make CardVector the inventory owner. Rejected because it duplicates
   CardUploader-managed state.
2. Treat the ETB JSON/Supabase registry as inventory truth. Rejected because it
   tracks capture/location capacity, not card-level allocation or lifecycle.
3. Wait for a live CardUploader API before defining ownership. Rejected because
   current development still needs a clear boundary.

## Consequences

- Exported CardUploader snapshots are read-only evidence until a supported live
  API exists.
- Existing ETB, audit, and Supabase location data remain compatibility
  projections and are not silently migrated.
- CardVector may not invent unsupported mutation, reservation, allocation,
  picking, or synchronization behavior.
- Orders retain order lifecycle; CardUploader owns inventory-side picking state.

## Compatibility And Migration

`CV-COMP-007` preserves ETB/location callers.
`CV-COMP-016` preserves `CardUploaderInventorySource`.
Removal requires a supported CardUploader API, caller migration, exact data
equivalence, and project-owner approval.

## Testing And Rollback

Tests must prove snapshot field, quantity, reconciliation, location projection,
pick-slip, serialization, and application-delegation equivalence without live
writes. Rollback reverts the Phase 5 commits; no database or schema rollback is
required.

## Approval

Approved by the project owner through explicit Phase 5 authorization.
