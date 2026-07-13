-- CardVector Mobile Capture production schema.
--
-- This migration keeps the MVP browser and desktop contracts compatible while
-- adding durable aliases required by the production model.

create schema if not exists public;

create or replace function public.cardvector_mobile_capture_touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace function public.cardvector_mobile_capture_normalize_session()
returns trigger
language plpgsql
as $$
begin
  if new.user_id is null then
    new.user_id = auth.uid();
  end if;

  if new.operator_id is null then
    new.operator_id = new.user_id;
  end if;

  if nullif(new.etb_location, '') is null and nullif(new.etb_location_id, '') is not null then
    new.etb_location = new.etb_location_id;
  end if;

  if nullif(new.etb_location_id, '') is null and nullif(new.etb_location, '') is not null then
    new.etb_location_id = new.etb_location;
  end if;

  if new.source_device = '{}'::jsonb and new.device <> '{}'::jsonb then
    new.source_device = new.device;
  end if;

  if new.device = '{}'::jsonb and new.source_device <> '{}'::jsonb then
    new.device = new.source_device;
  end if;

  if nullif(new.conversion_status, '') is null then
    new.conversion_status = new.status;
  end if;

  return new;
end;
$$;

create table if not exists public.mobile_capture_sessions (
  capture_session_id text primary key,
  etb_location text,
  etb_location_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  submitted_at timestamptz,
  status text not null default 'DRAFT',
  source text not null default 'MOBILE_WEB',
  operator text,
  operator_id uuid references auth.users(id),
  user_id uuid references auth.users(id),
  device jsonb not null default '{}'::jsonb,
  source_device jsonb not null default '{}'::jsonb,
  image_count integer not null default 0,
  original_image_locations jsonb not null default '[]'::jsonb,
  conversion_status text,
  conversion_workstation text,
  error_message text,
  schema_version integer not null default 1,
  constraint mobile_capture_sessions_status_chk check (
    status in ('DRAFT', 'UPLOADING', 'PENDING_CONVERSION', 'PROCESSING', 'CONVERTED', 'FAILED', 'CANCELLED')
  ),
  constraint mobile_capture_sessions_conversion_status_chk check (
    conversion_status is null
    or conversion_status = ''
    or conversion_status in ('DRAFT', 'UPLOADING', 'PENDING_CONVERSION', 'PROCESSING', 'CONVERTED', 'FAILED', 'CANCELLED')
  ),
  constraint mobile_capture_sessions_source_chk check (source = 'MOBILE_WEB'),
  constraint mobile_capture_sessions_image_count_chk check (image_count >= 0)
);

alter table public.mobile_capture_sessions
  add column if not exists etb_location_id text,
  add column if not exists operator_id uuid references auth.users(id),
  add column if not exists source_device jsonb not null default '{}'::jsonb,
  add column if not exists error_message text,
  add column if not exists schema_version integer not null default 1;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'mobile_capture_sessions_etb_location_present_chk'
      and conrelid = 'public.mobile_capture_sessions'::regclass
  ) then
    alter table public.mobile_capture_sessions
      add constraint mobile_capture_sessions_etb_location_present_chk
      check (nullif(etb_location, '') is not null or nullif(etb_location_id, '') is not null);
  end if;
end;
$$;

create or replace trigger mobile_capture_sessions_normalize_before_write
before insert or update on public.mobile_capture_sessions
for each row execute function public.cardvector_mobile_capture_normalize_session();

create or replace trigger mobile_capture_sessions_touch_updated_at
before update on public.mobile_capture_sessions
for each row execute function public.cardvector_mobile_capture_touch_updated_at();

create index if not exists mobile_capture_sessions_status_idx
  on public.mobile_capture_sessions(status, submitted_at);

create index if not exists mobile_capture_sessions_etb_location_idx
  on public.mobile_capture_sessions(etb_location_id, status);

create table if not exists public.mobile_capture_images (
  image_id text primary key,
  capture_session_id text not null references public.mobile_capture_sessions(capture_session_id) on delete cascade,
  image_order integer,
  sequence_number integer,
  storage_bucket text not null default 'mobile-capture-originals',
  storage_path text not null,
  original_filename text,
  content_type text not null,
  byte_size bigint,
  upload_status text not null default 'UPLOADED',
  sha256 text,
  width integer,
  height integer,
  created_at timestamptz not null default now(),
  removed_at timestamptz,
  user_id uuid references auth.users(id),
  constraint mobile_capture_images_order_chk check (
    coalesce(image_order, sequence_number) is not null
    and coalesce(image_order, sequence_number) > 0
  ),
  constraint mobile_capture_images_size_chk check (byte_size is null or byte_size >= 0),
  constraint mobile_capture_images_dimensions_chk check (
    (width is null or width > 0)
    and (height is null or height > 0)
  ),
  constraint mobile_capture_images_upload_status_chk check (
    upload_status in ('UPLOADING', 'UPLOADED', 'FAILED', 'REMOVED')
  )
);

alter table public.mobile_capture_images
  add column if not exists image_order integer,
  add column if not exists upload_status text not null default 'UPLOADED',
  add column if not exists width integer,
  add column if not exists height integer;

create or replace function public.cardvector_mobile_capture_normalize_image()
returns trigger
language plpgsql
as $$
begin
  if new.user_id is null then
    select s.user_id
      into new.user_id
      from public.mobile_capture_sessions s
     where s.capture_session_id = new.capture_session_id;
  end if;

  if new.image_order is null and new.sequence_number is not null then
    new.image_order = new.sequence_number;
  end if;

  if new.sequence_number is null and new.image_order is not null then
    new.sequence_number = new.image_order;
  end if;

  return new;
end;
$$;

create or replace trigger mobile_capture_images_normalize_before_write
before insert or update on public.mobile_capture_images
for each row execute function public.cardvector_mobile_capture_normalize_image();

create index if not exists mobile_capture_images_session_idx
  on public.mobile_capture_images(capture_session_id, sequence_number);

create unique index if not exists mobile_capture_images_session_order_unique_idx
  on public.mobile_capture_images(capture_session_id, coalesce(image_order, sequence_number))
  where removed_at is null;

create unique index if not exists mobile_capture_images_storage_path_unique_idx
  on public.mobile_capture_images(storage_bucket, storage_path);

alter table public.mobile_capture_sessions enable row level security;
alter table public.mobile_capture_images enable row level security;

drop policy if exists "operators insert own mobile capture sessions" on public.mobile_capture_sessions;
drop policy if exists "operators read own mobile capture sessions" on public.mobile_capture_sessions;
drop policy if exists "operators update own draft mobile capture sessions" on public.mobile_capture_sessions;
drop policy if exists "operators insert own mobile capture images" on public.mobile_capture_images;
drop policy if exists "operators read own mobile capture images" on public.mobile_capture_images;
drop policy if exists "operators update own mobile capture images" on public.mobile_capture_images;

create policy "operators insert own mobile capture sessions"
  on public.mobile_capture_sessions
  for insert
  to authenticated
  with check (user_id = auth.uid() and source = 'MOBILE_WEB');

create policy "operators read own mobile capture sessions"
  on public.mobile_capture_sessions
  for select
  to authenticated
  using (user_id = auth.uid());

create policy "operators update own draft mobile capture sessions"
  on public.mobile_capture_sessions
  for update
  to authenticated
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and status in ('DRAFT', 'UPLOADING', 'PENDING_CONVERSION', 'CANCELLED', 'FAILED')
  );

create policy "operators insert own mobile capture images"
  on public.mobile_capture_images
  for insert
  to authenticated
  with check (
    user_id = auth.uid()
    and exists (
      select 1
        from public.mobile_capture_sessions s
       where s.capture_session_id = mobile_capture_images.capture_session_id
         and s.user_id = auth.uid()
         and s.status in ('DRAFT', 'UPLOADING')
    )
  );

create policy "operators read own mobile capture images"
  on public.mobile_capture_images
  for select
  to authenticated
  using (user_id = auth.uid());

create policy "operators update own mobile capture images"
  on public.mobile_capture_images
  for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'mobile-capture-originals',
  'mobile-capture-originals',
  false,
  25000000,
  array['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp']
)
on conflict (id) do update
set public = false,
    file_size_limit = 25000000,
    allowed_mime_types = array['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'];

drop policy if exists "operators upload mobile originals" on storage.objects;
drop policy if exists "operators read mobile originals" on storage.objects;
drop policy if exists "operators update mobile originals" on storage.objects;
drop policy if exists "operators delete draft mobile originals" on storage.objects;

create policy "operators upload mobile originals"
  on storage.objects
  for insert
  to authenticated
  with check (
    bucket_id = 'mobile-capture-originals'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "operators read mobile originals"
  on storage.objects
  for select
  to authenticated
  using (
    bucket_id = 'mobile-capture-originals'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "operators update mobile originals"
  on storage.objects
  for update
  to authenticated
  using (
    bucket_id = 'mobile-capture-originals'
    and (storage.foldername(name))[1] = auth.uid()::text
  )
  with check (
    bucket_id = 'mobile-capture-originals'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Draft cleanup only. Production originals should be retained after submit.
create policy "operators delete draft mobile originals"
  on storage.objects
  for delete
  to authenticated
  using (
    bucket_id = 'mobile-capture-originals'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
