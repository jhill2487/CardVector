-- CardVector canonical capture/location registry.
--
-- This migration establishes Supabase as the canonical shared registry for
-- CardVector capture batches, storage locations, ETBs/containers, capture
-- images, and lightweight external-inventory relationships. It intentionally
-- does not migrate managed card inventory ownership or alter existing legacy
-- mobile-capture tables. Legacy tables and JSON registries remain compatibility
-- inputs until cutover is validated.

create extension if not exists pgcrypto;

create or replace function public.cardvector_registry_touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.cardvector_location_operators (
  user_id uuid primary key references auth.users(id) on delete cascade,
  can_manage_locations boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.cardvector_storage_locations (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid references auth.users(id) on delete set null,
  organization_id text,
  parent_location_id uuid references public.cardvector_storage_locations(id) on delete restrict,
  name text not null,
  description text not null default '',
  location_type text not null default 'custom',
  status text not null default 'active',
  source text not null default 'cardvector',
  legacy_id text,
  legacy_etb_id text,
  legacy_location_code text,
  display_code text,
  capacity integer,
  stored_count integer not null default 0,
  sync_state text not null default 'synced',
  metadata jsonb not null default '{}'::jsonb,
  migration_metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id),
  updated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint cardvector_storage_locations_type_chk check (
    location_type in (
      'room', 'closet', 'shelf', 'drawer', 'cabinet', 'etb', 'box',
      'binder', 'bin', 'slot', 'custom'
    )
  ),
  constraint cardvector_storage_locations_status_chk check (
    status in (
      'empty', 'active', 'full', 'location_complete', 'needs_review',
      'staged', 'inactive', 'archived', 'unknown'
    )
  ),
  constraint cardvector_storage_locations_count_chk check (stored_count >= 0),
  constraint cardvector_storage_locations_capacity_chk check (
    capacity is null or capacity > 0
  ),
  constraint cardvector_storage_locations_slot_code_chk check (
    legacy_location_code is null or legacy_location_code ~ '^[A-J]$'
  )
);

create unique index if not exists cardvector_storage_locations_legacy_id_idx
  on public.cardvector_storage_locations(owner_user_id, legacy_id)
  where legacy_id is not null;

create unique index if not exists cardvector_storage_locations_display_code_idx
  on public.cardvector_storage_locations(owner_user_id, display_code)
  where display_code is not null and archived_at is null;

create index if not exists cardvector_storage_locations_parent_idx
  on public.cardvector_storage_locations(parent_location_id, location_type);

create index if not exists cardvector_storage_locations_owner_type_idx
  on public.cardvector_storage_locations(owner_user_id, location_type, status);

create table if not exists public.cardvector_capture_sessions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid references auth.users(id) on delete set null,
  organization_id text,
  source_application text not null default 'CardVector.app',
  originating_device jsonb not null default '{}'::jsonb,
  location_id uuid references public.cardvector_storage_locations(id) on delete set null,
  status text not null default 'draft',
  photo_count integer not null default 0,
  processed_count integer not null default 0,
  recognized_count integer not null default 0,
  failed_count integer not null default 0,
  sync_state text not null default 'synced',
  legacy_session_id text,
  legacy_capture_type text,
  legacy_etb_location_id text,
  migration_metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id),
  updated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  archived_at timestamptz,
  constraint cardvector_capture_sessions_status_chk check (
    status in (
      'draft', 'uploading', 'pending_processing', 'staged', 'processing',
      'processed', 'completed', 'failed', 'cancelled', 'archived'
    )
  ),
  constraint cardvector_capture_sessions_count_chk check (
    photo_count >= 0 and processed_count >= 0 and recognized_count >= 0
    and failed_count >= 0
  )
);

create unique index if not exists cardvector_capture_sessions_legacy_idx
  on public.cardvector_capture_sessions(owner_user_id, legacy_session_id);

create index if not exists cardvector_capture_sessions_location_idx
  on public.cardvector_capture_sessions(location_id, status, updated_at);

create index if not exists cardvector_capture_sessions_owner_status_idx
  on public.cardvector_capture_sessions(owner_user_id, status, updated_at);

create table if not exists public.cardvector_capture_images (
  id uuid primary key default gen_random_uuid(),
  capture_session_id uuid not null references public.cardvector_capture_sessions(id) on delete cascade,
  owner_user_id uuid references auth.users(id) on delete set null,
  storage_bucket text not null default 'mobile-capture-originals',
  storage_object_path text not null,
  original_filename text,
  sequence_number integer not null,
  upload_status text not null default 'uploaded',
  processing_status text not null default 'pending',
  checksum text,
  byte_size bigint,
  width integer,
  height integer,
  legacy_image_id text,
  migration_metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id),
  updated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint cardvector_capture_images_sequence_chk check (sequence_number > 0),
  constraint cardvector_capture_images_upload_status_chk check (
    upload_status in ('uploading', 'uploaded', 'failed', 'removed')
  ),
  constraint cardvector_capture_images_processing_status_chk check (
    processing_status in ('pending', 'staged', 'processing', 'processed', 'failed', 'removed')
  ),
  constraint cardvector_capture_images_size_chk check (byte_size is null or byte_size >= 0),
  constraint cardvector_capture_images_dimensions_chk check (
    (width is null or width > 0) and (height is null or height > 0)
  )
);

create unique index if not exists cardvector_capture_images_session_sequence_idx
  on public.cardvector_capture_images(capture_session_id, sequence_number)
  where archived_at is null;

create unique index if not exists cardvector_capture_images_storage_path_idx
  on public.cardvector_capture_images(owner_user_id, storage_bucket, storage_object_path);

create index if not exists cardvector_capture_images_owner_idx
  on public.cardvector_capture_images(owner_user_id, created_at);

create table if not exists public.cardvector_inventory_relationships (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid references auth.users(id) on delete set null,
  capture_session_id uuid references public.cardvector_capture_sessions(id) on delete set null,
  capture_image_id uuid references public.cardvector_capture_images(id) on delete set null,
  location_id uuid references public.cardvector_storage_locations(id) on delete set null,
  external_inventory_provider text,
  external_inventory_id text,
  relationship_type text not null default 'capture_context',
  status text not null default 'active',
  legacy_id text,
  metadata jsonb not null default '{}'::jsonb,
  migration_metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id),
  updated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint cardvector_inventory_relationships_type_chk check (
    relationship_type in (
      'capture_context', 'recognized_card', 'external_inventory_reference',
      'location_assignment'
    )
  ),
  constraint cardvector_inventory_relationships_status_chk check (
    status in ('active', 'pending', 'confirmed', 'rejected', 'archived')
  )
);

create unique index if not exists cardvector_inventory_relationships_external_idx
  on public.cardvector_inventory_relationships(
    owner_user_id,
    external_inventory_provider,
    external_inventory_id,
    relationship_type
  )
  where external_inventory_provider is not null
    and external_inventory_id is not null
    and archived_at is null;

create index if not exists cardvector_inventory_relationships_capture_idx
  on public.cardvector_inventory_relationships(capture_session_id, relationship_type);

drop trigger if exists cardvector_location_operators_touch_updated_at
  on public.cardvector_location_operators;
create trigger cardvector_location_operators_touch_updated_at
before update on public.cardvector_location_operators
for each row execute function public.cardvector_registry_touch_updated_at();

drop trigger if exists cardvector_storage_locations_touch_updated_at
  on public.cardvector_storage_locations;
create trigger cardvector_storage_locations_touch_updated_at
before update on public.cardvector_storage_locations
for each row execute function public.cardvector_registry_touch_updated_at();

drop trigger if exists cardvector_capture_sessions_touch_updated_at
  on public.cardvector_capture_sessions;
create trigger cardvector_capture_sessions_touch_updated_at
before update on public.cardvector_capture_sessions
for each row execute function public.cardvector_registry_touch_updated_at();

drop trigger if exists cardvector_capture_images_touch_updated_at
  on public.cardvector_capture_images;
create trigger cardvector_capture_images_touch_updated_at
before update on public.cardvector_capture_images
for each row execute function public.cardvector_registry_touch_updated_at();

drop trigger if exists cardvector_inventory_relationships_touch_updated_at
  on public.cardvector_inventory_relationships;
create trigger cardvector_inventory_relationships_touch_updated_at
before update on public.cardvector_inventory_relationships
for each row execute function public.cardvector_registry_touch_updated_at();

alter table public.cardvector_location_operators enable row level security;
alter table public.cardvector_storage_locations enable row level security;
alter table public.cardvector_capture_sessions enable row level security;
alter table public.cardvector_capture_images enable row level security;
alter table public.cardvector_inventory_relationships enable row level security;

drop policy if exists "operators read own location authorization"
  on public.cardvector_location_operators;
create policy "operators read own location authorization"
  on public.cardvector_location_operators
  for select
  to authenticated
  using (user_id = auth.uid());

drop policy if exists "operators manage own storage locations"
  on public.cardvector_storage_locations;
create policy "operators manage own storage locations"
  on public.cardvector_storage_locations
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

drop policy if exists "authorized operators read storage locations"
  on public.cardvector_storage_locations;
create policy "authorized operators read storage locations"
  on public.cardvector_storage_locations
  for select
  to authenticated
  using (
    owner_user_id = auth.uid()
    or exists (
      select 1
        from public.cardvector_location_operators operator_access
       where operator_access.user_id = auth.uid()
         and operator_access.can_manage_locations
    )
  );

drop policy if exists "operators manage own capture sessions"
  on public.cardvector_capture_sessions;
create policy "operators manage own capture sessions"
  on public.cardvector_capture_sessions
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

drop policy if exists "operators manage own capture images"
  on public.cardvector_capture_images;
create policy "operators manage own capture images"
  on public.cardvector_capture_images
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

drop policy if exists "operators manage own inventory relationships"
  on public.cardvector_inventory_relationships;
create policy "operators manage own inventory relationships"
  on public.cardvector_inventory_relationships
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

revoke all on table public.cardvector_location_operators from anon;
revoke all on table public.cardvector_storage_locations from anon;
revoke all on table public.cardvector_capture_sessions from anon;
revoke all on table public.cardvector_capture_images from anon;
revoke all on table public.cardvector_inventory_relationships from anon;

grant select on table public.cardvector_location_operators to authenticated;
grant select, insert, update on table public.cardvector_storage_locations to authenticated;
grant select, insert, update on table public.cardvector_capture_sessions to authenticated;
grant select, insert, update on table public.cardvector_capture_images to authenticated;
grant select, insert, update on table public.cardvector_inventory_relationships to authenticated;

grant select, insert, update on table public.cardvector_location_operators to service_role;
grant select, insert, update on table public.cardvector_storage_locations to service_role;
grant select, insert, update on table public.cardvector_capture_sessions to service_role;
grant select, insert, update on table public.cardvector_capture_images to service_role;
grant select, insert, update on table public.cardvector_inventory_relationships to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'mobile-capture-originals',
  'mobile-capture-originals',
  false,
  26214400,
  array[
    'image/jpeg',
    'image/png',
    'image/heic',
    'image/heif',
    'image/webp'
  ]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "operators upload canonical mobile originals" on storage.objects;
create policy "operators upload canonical mobile originals"
  on storage.objects
  for insert
  to authenticated
  with check (
    bucket_id = 'mobile-capture-originals'
    and split_part(name, '/', 1) = auth.uid()::text
  );

drop policy if exists "operators read canonical mobile originals" on storage.objects;
create policy "operators read canonical mobile originals"
  on storage.objects
  for select
  to authenticated
  using (
    bucket_id = 'mobile-capture-originals'
    and split_part(name, '/', 1) = auth.uid()::text
  );

drop policy if exists "operators update canonical mobile originals" on storage.objects;
create policy "operators update canonical mobile originals"
  on storage.objects
  for update
  to authenticated
  using (
    bucket_id = 'mobile-capture-originals'
    and split_part(name, '/', 1) = auth.uid()::text
  )
  with check (
    bucket_id = 'mobile-capture-originals'
    and split_part(name, '/', 1) = auth.uid()::text
  );

create or replace view public.cardvector_etb_location_registry_v as
select
  etb.id as etb_location_uuid,
  etb.display_code as etb_id,
  etb.name as etb_name,
  etb.status as etb_status,
  slot.id as slot_location_uuid,
  slot.display_code as location_id,
  slot.legacy_location_code as location_code,
  slot.status as location_status,
  slot.capacity,
  slot.stored_count,
  slot.sync_state,
  greatest(etb.updated_at, coalesce(slot.updated_at, etb.updated_at)) as updated_at
from public.cardvector_storage_locations etb
left join public.cardvector_storage_locations slot
  on slot.parent_location_id = etb.id
 and slot.location_type = 'slot'
 and slot.archived_at is null
where etb.location_type = 'etb'
  and etb.archived_at is null;

create or replace function public.cardvector_create_next_etb_slot(
  p_etb_display_code text,
  p_expected_slot_code text default null
)
returns table (
  id uuid,
  location_id text,
  etb_id text,
  location_code text,
  status text,
  capacity integer,
  stored_count integer,
  created_at timestamptz,
  updated_at timestamptz
)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_user_id uuid := auth.uid();
  v_etb_display_code text := upper(btrim(coalesce(p_etb_display_code, '')));
  v_expected text := upper(btrim(coalesce(p_expected_slot_code, '')));
  v_etb public.cardvector_storage_locations%rowtype;
  v_next_code text;
  v_created public.cardvector_storage_locations%rowtype;
begin
  if v_user_id is null then
    raise exception using errcode = '42501', message = 'Authentication required.';
  end if;

  if not exists (
    select 1
      from public.cardvector_location_operators operator_access
     where operator_access.user_id = v_user_id
       and operator_access.can_manage_locations
  ) then
    raise exception using errcode = '42501', message = 'Location-management authorization required.';
  end if;

  if v_etb_display_code !~ '^ETB-[0-9]{3}$' then
    raise exception using errcode = '22023', message = 'ETB ID must use ETB-### format.';
  end if;

  if v_expected <> '' and v_expected !~ '^[A-J]$' then
    raise exception using errcode = '22023', message = 'Expected location code must be A-J.';
  end if;

  select *
    into v_etb
    from public.cardvector_storage_locations
   where location_type = 'etb'
     and display_code = v_etb_display_code
     and archived_at is null
   order by created_at
   limit 1
   for update;

  if v_etb.id is null then
    raise exception using errcode = 'P0002', message = 'ETB not found.';
  end if;

  select allowed.location_code
    into v_next_code
    from unnest(array['A','B','C','D','E','F','G','H','I','J'])
         with ordinality as allowed(location_code, sequence_number)
   where not exists (
     select 1
       from public.cardvector_storage_locations existing
      where existing.parent_location_id = v_etb.id
        and existing.location_type = 'slot'
        and existing.legacy_location_code = allowed.location_code
        and existing.archived_at is null
   )
   order by allowed.sequence_number
   limit 1;

  if v_next_code is null then
    raise exception using errcode = '23514', message = 'No available location remains for this ETB.';
  end if;

  if v_expected <> '' and v_expected <> v_next_code then
    raise exception using errcode = '40001', message = 'Location availability changed. Refresh and confirm the new proposal.';
  end if;

  insert into public.cardvector_storage_locations (
    owner_user_id,
    parent_location_id,
    name,
    location_type,
    status,
    source,
    legacy_id,
    legacy_etb_id,
    legacy_location_code,
    display_code,
    capacity,
    stored_count,
    created_by,
    updated_by,
    migration_metadata
  ) values (
    v_etb.owner_user_id,
    v_etb.id,
    v_etb_display_code || '-' || v_next_code,
    'slot',
    'empty',
    'cardvector_app',
    v_etb_display_code || '-' || v_next_code,
    v_etb_display_code,
    v_next_code,
    v_etb_display_code || '-' || v_next_code,
    40,
    0,
    v_user_id,
    v_user_id,
    jsonb_build_object('created_by_rpc', 'cardvector_create_next_etb_slot')
  )
  returning * into v_created;

  return query
  select
    v_created.id,
    v_created.display_code,
    v_etb.display_code,
    v_created.legacy_location_code,
    v_created.status,
    v_created.capacity,
    v_created.stored_count,
    v_created.created_at,
    v_created.updated_at;
end;
$$;

revoke all on function public.cardvector_create_next_etb_slot(text, text) from public;
revoke all on function public.cardvector_create_next_etb_slot(text, text) from anon;
grant execute on function public.cardvector_create_next_etb_slot(text, text) to authenticated;
