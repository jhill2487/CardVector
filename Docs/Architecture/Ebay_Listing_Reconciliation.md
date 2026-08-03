# eBay Listing Reconciliation

**Status:** Phase eBay Listing Reconciliation v1 implemented as a CSV snapshot workflow.

## Facts

- eBay is the source of truth for live marketplace listing state.
- CardUploader remains the source of truth for managed inventory and card-level inventory status.
- CardVector.app is the primary future operator UI.
- Marketplace Intelligence owns pricing recommendations, not listing record authority.
- The v1 workflow must not revise, end, publish, or otherwise mutate live eBay listings.

## Decision

CardVector.app may import authenticated eBay active-listing CSV snapshots into
Supabase for reconciliation review. The imported rows are evidence snapshots,
not live marketplace controls.

The v1 canonical Supabase tables are:

- `public.cardvector_marketplace_listing_snapshots`
- `public.cardvector_inventory_listing_matches`
- `public.cardvector_ebay_listing_reconciliation_v`

`marketplace_listing_id` is the stable listing identity for eBay snapshots.
SKU and ETB/location labels are review signals because they may change as the
physical-location naming convention evolves.

## Ownership

- **Listings/eBay reconciliation:** CardVector listing workflow and future eBay integration.
- **Inventory truth:** CardUploader.
- **Pricing:** Marketplace Intelligence.
- **Operator presentation:** CardVector.app.
- **Persistence:** Supabase, scoped by authenticated operator ownership.

## V1 Workflow

1. Operator signs into CardVector.app.
2. Operator opens `/operator/listings`.
3. Operator selects an eBay active-listings CSV.
4. The browser parses item ID, SKU, title, price, quantity, condition, listing status, and location hints.
5. The review page flags missing SKUs, duplicate SKUs, duplicate item IDs, and location hints.
6. Operator may import the snapshot into Supabase.
7. Rows with duplicate eBay item IDs are held for manual review rather than imported.
8. No live eBay marketplace action occurs.

## Review Buckets

The operator page computes review buckets in the browser without updating the
imported evidence rows:

- `matched`: a unique nonblank eBay SKU carries an ETB/location hint that has a
  CardUploader batch reference.
- `ebay_only`: a unique nonblank eBay SKU has no ETB/location reference.
- `duplicate_sku`: the normalized SKU appears on more than one active eBay
  snapshot.
- `missing_sku`: the eBay snapshot has no SKU.
- `needs_manual_review`: the snapshot carries an ETB/location hint that is not
  represented by a CardUploader batch reference.
- `missing_from_ebay`: a CardUploader batch/location reference has no matched
  eBay snapshot.

`missing_from_ebay` is a reference-level gap, not proof that an individual
CardUploader inventory item is absent from eBay. The available Supabase batch
references contain batch and location metadata, not card-level SKU inventory.

## Acceptance Criteria

- Existing listing review is reachable from the Operator Dashboard.
- eBay active-listing CSV rows can be parsed in the browser.
- Snapshot rows are upserted by `owner_user_id`, `marketplace`, and `marketplace_listing_id`.
- Match review rows are linked to listing snapshots.
- RLS is enabled on both tables.
- Anonymous access is revoked.
- The workflow contains no live eBay mutation calls.

## Rollback

- Revert the app/source commit to remove the operator page.
- If the Supabase migration has been applied, leave snapshot tables in place until
  the operator confirms no imported evidence is needed, then archive/drop through
  a reviewed SQL migration.
