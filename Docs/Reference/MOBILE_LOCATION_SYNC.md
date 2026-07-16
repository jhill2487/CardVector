# CardVector Mobile Location Synchronization

Status: Production contract pending Supabase migration activation

## Source Of Truth

Supabase is authoritative for cloud-visible ETB and location identity:

- which ETBs Mobile may list
- which A-J locations have been provisioned
- canonical `ETB-###-A` location IDs
- secure atomic creation of the next location

The desktop registry at
`Platform/Putnam_OS/System/data/inventory/etb_location_registry.json` remains
the offline operational projection for:

- occupancy and capacity
- operational status
- active location
- assigned batches and CardUploader references
- QR and label generation

These are complementary field owners, not competing registries. Cloud identity
is merged into the desktop projection. Mobile does not edit counts, capacity,
status, batches, or inventory.

## Synchronization Contract

`mobile_capture_queue.py sync-locations` performs a controlled two-way adapter:

1. Validated local ETBs are upserted to `cardvector_etbs` with the desktop
   service-role credential.
2. Operationally used or explicitly cloud-provisioned A-J slots are upserted to
   `cardvector_locations`. Earlier letters are included to preserve sequence.
3. Cloud ETBs and locations are read back.
4. Cloud-created identities are marked `cloud_provisioned` in the local JSON
   projection without overwriting local occupancy or status.

Capture Queue refresh and processing call this adapter best-effort. If the new
tables are not deployed or Supabase is unavailable, capture listing, claiming,
staging, and routing continue normally. The explicit CLI command is strict and
reports synchronization errors.

## Canonical Rules

- ETB: `ETB-###`
- Location code: `A` through `J`
- Location ID: `ETB-###-A`
- ETB capacity: `400`
- Location capacity: `40`
- New location status: `Empty`

The desktop validators remain the canonical application rules. The migration
enforces the same formats, capacities, sequence, and uniqueness in Postgres.

## Secure Creation

The browser cannot insert into location tables. It calls the authenticated
`cardvector_create_next_location` RPC with the ETB and the location proposal the
operator approved.

The RPC:

- requires `auth.uid()`
- requires `cardvector_location_operators.can_manage_locations = true`
- validates the ETB and expected A-J code
- locks the ETB row with `FOR UPDATE`
- recomputes the first missing A-J code inside the transaction
- rejects stale proposals and exhausted ETBs
- relies on primary/composite uniqueness constraints

Anonymous execution and authenticated direct inserts are revoked.

## Production Activation

Apply:

```text
supabase/migrations/20260716130000_mobile_location_registry.sql
```

Then authorize the intended Supabase Auth operator in the SQL editor:

```sql
insert into public.cardvector_location_operators (user_id, can_manage_locations)
values ('<AUTH_USER_UUID>', true)
on conflict (user_id) do update
set can_manage_locations = excluded.can_manage_locations;
```

Run the initial desktop synchronization:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py sync-locations
```

Do not put the service-role key or an operator UUID in public website files.

## Mobile Entry Routes

- `/location/<ETB-ID>/<LOCATION>`: known location, then capture-type choice.
- `/etb/<ETB-ID>`: capture type, locations, view, and secure next-location flow.
- `/capture`: capture type, ETB, location/create, review, then explicit start.
- `/capture/<ETB-ID>/<LOCATION>/<capture-type>`: the existing camera screen.

Only the final camera route starts the camera, and it is reached through an
explicit operator action.
