# Canonical Model And Legacy Mapping

## Supabase Tables

The versioned migration is:

`supabase/migrations/20260725090000_canonical_capture_location_registry.sql`

It creates:

- `cardvector_storage_locations`
- `cardvector_capture_sessions`
- `cardvector_capture_images`
- `cardvector_inventory_relationships`
- `cardvector_etb_location_registry_v`
- `cardvector_create_next_etb_slot(...)`

## ETB Decision

ETBs are canonical location rows:

- ETB row: `location_type = 'etb'`, `display_code = 'ETB-###'`
- Slot row: `location_type = 'slot'`, `parent_location_id = ETB.id`,
  `display_code = 'ETB-###-A'`

This preserves the existing ETB/location behavior without creating two
authoritative physical-location registries.

## Location Mapping

| Legacy field | Canonical field |
| --- | --- |
| ETB `location_code` or `etb_id` | `display_code`, `legacy_etb_id`, `legacy_id` |
| Child `location_id` | `display_code`, `legacy_id` |
| Child `location_code` | `legacy_location_code` |
| `status` | `status` after compatibility mapping |
| `total_capacity` / `estimated_capacity` | `capacity` on ETB row |
| Child `capacity` | `capacity` on slot row |
| `stored_count` | `stored_count` |
| `assigned_batch` and CardUploader batch fields | `metadata` |
| source file and source updated time | `migration_metadata` |

## Capture Session Mapping

| Legacy field | Canonical field |
| --- | --- |
| `mobile_capture_session_id` or `session_id` | `legacy_session_id` |
| deterministic UUID from legacy session | `id` |
| `location_id` | `legacy_etb_location_id`; resolved to `location_id` when possible |
| `status` | `status` after canonical state mapping |
| `session_type` | `legacy_capture_type` |
| `photos_captured` / `cards_captured` | `photo_count` |
| `capture_folder`, `capture_session_file` | `migration_metadata` |
| timestamps | `created_at`, `updated_at`, `completed_at` |

## Capture Image Mapping

| Legacy field | Canonical field |
| --- | --- |
| `mobile_image_id` or stable session/index fallback | `legacy_image_id` |
| deterministic UUID from legacy image | `id` |
| canonical session UUID | `capture_session_id` |
| `mobile_storage_bucket` | `storage_bucket` |
| `mobile_storage_path` or `path` | `storage_object_path` |
| `filename` | `original_filename` |
| record order | `sequence_number` |
| side and card number | `migration_metadata` |

## Status Transitions

Canonical capture statuses:

- `draft`
- `uploading`
- `pending_processing`
- `staged`
- `processing`
- `processed`
- `completed`
- `failed`
- `cancelled`
- `archived`

Legacy mappings:

- `Mobile Capture Staged` -> `staged`
- `Location Complete` -> `completed` for capture sessions
- `Location Complete` -> `location_complete` for storage locations
- `PENDING_CONVERSION` -> `pending_processing` in CardVector.app writes

## Inventory Relationship Boundary

`cardvector_inventory_relationships` stores only lightweight links between a
capture session/image/location and an external inventory identifier. It is not a
managed-inventory table and must not store authoritative quantities,
reservations, allocations, or picking state.
