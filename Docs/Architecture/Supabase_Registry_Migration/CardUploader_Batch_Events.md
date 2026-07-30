# CardUploader Batch Events

## Decision

CardUploader batch history links are recorded as Supabase-backed batch events
attached to canonical CardVector storage locations.

CardUploader remains the source of managed card-level inventory truth. eBay
remains the source of listed marketplace truth. Supabase stores the shared
capture/location registry and the references needed for CardVector OS and
CardVector.app to display the same ETB and location context.

## Data Boundary

`cardvector_carduploader_batch_events` stores historical provenance:

- CardUploader batch ID and URL
- ETB/location display code when known
- optional card count and value reported by CardUploader
- batch date, game, language, and event type
- source scrape metadata

The table does not store authoritative inventory quantities. A CardUploader
batch card count must not update `cardvector_storage_locations.stored_count`.
Locations may have multiple batch events because inventory can be refilled after
sales.

## Backfill Behavior

`Tools/backfill_carduploader_batch_events.py` reads scraped CardUploader batch
history and the legacy ETB registry.

Dry-run output classifies records as:

- `location_event`: explicit ETB slot can be recorded as historical provenance
- `already_linked`: existing legacy registry field already references the batch
- `needs_physical_conversion`: label names an ETB but not an A-J slot
- `unassigned_no_location`: no safe location can be inferred
- `missing_registry_location`: explicit slot is not present in the registry

The current dry run from the scraped CardUploader history produced:

- 27 location events
- 1 already-linked event
- 5 ETB-only records requiring physical conversion review
- 1 unassigned record

## Rollout

1. Apply the schema migration after review.
2. Run the backfill planner in dry-run mode.
3. Review `needs_physical_conversion` and `unassigned_no_location` rows.
4. Apply local cache backfill only when approved.
5. Upsert approved `location_event` and `already_linked` rows to Supabase.
6. Keep legacy JSON as a fallback/cache until cutover validation passes.
