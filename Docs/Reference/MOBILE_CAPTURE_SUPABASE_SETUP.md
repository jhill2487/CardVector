# Mobile Capture Supabase Setup

Status: Production setup notes

Date: 2026-07-13

## Scope

Mobile Capture uses Supabase for authenticated mobile uploads, capture-session metadata, and original-image storage.

GitHub Pages remains the static host for `cardvector.app`. The browser receives only public Supabase configuration. Service-role credentials are used only by trusted desktop queue processing tools.

## Required Supabase Resources

- Supabase Auth with operator accounts.
- Table: `mobile_capture_sessions`.
- Table: `mobile_capture_images`.
- Storage bucket: `mobile-capture-originals`.

## Environment Variables

Static web configuration:

- `Docs/mobile-capture-config.js`
  - `supabaseUrl`
  - `supabaseAnonKey`
  - `originalImageBucket`

Desktop queue processor:

- `CARDVECTOR_SUPABASE_URL`
- `CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY`

The service-role key must never be committed and must never be exposed in browser JavaScript.

## SQL

Run this in the Supabase SQL editor before enabling production uploads.

```sql
create table if not exists public.mobile_capture_sessions (
  capture_session_id text primary key,
  etb_location text not null,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  submitted_at timestamptz,
  status text not null check (
    status in ('DRAFT', 'UPLOADING', 'PENDING_CONVERSION', 'PROCESSING', 'CONVERTED', 'FAILED', 'CANCELLED')
  ),
  source text not null default 'MOBILE_WEB',
  operator text,
  device jsonb not null default '{}'::jsonb,
  image_count integer not null default 0,
  original_image_locations jsonb not null default '[]'::jsonb,
  conversion_status text,
  conversion_workstation text,
  error_message text,
  schema_version integer not null default 1,
  user_id uuid references auth.users(id)
);

create table if not exists public.mobile_capture_images (
  image_id text primary key,
  capture_session_id text not null references public.mobile_capture_sessions(capture_session_id) on delete cascade,
  storage_bucket text not null,
  storage_path text not null,
  original_filename text,
  content_type text not null,
  byte_size bigint,
  sha256 text,
  sequence_number integer not null,
  created_at timestamptz not null,
  removed_at timestamptz,
  user_id uuid references auth.users(id)
);

create index if not exists mobile_capture_sessions_status_idx
  on public.mobile_capture_sessions(status, submitted_at);

create index if not exists mobile_capture_images_session_idx
  on public.mobile_capture_images(capture_session_id, sequence_number);

alter table public.mobile_capture_sessions enable row level security;
alter table public.mobile_capture_images enable row level security;

create policy "operators insert own mobile capture sessions"
  on public.mobile_capture_sessions
  for insert
  to authenticated
  with check (user_id = auth.uid());

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
  with check (user_id = auth.uid());

create policy "operators insert own mobile capture images"
  on public.mobile_capture_images
  for insert
  to authenticated
  with check (user_id = auth.uid());

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
```

Create the private storage bucket:

```sql
insert into storage.buckets (id, name, public)
values ('mobile-capture-originals', 'mobile-capture-originals', false)
on conflict (id) do nothing;

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
```

The desktop processor uses the service-role key, which bypasses RLS for queue listing, atomic claim, image download, and status updates.

## Desktop Queue Commands

List pending sessions:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py list
```

Claim and stage one session:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py process <capture_session_id>
```

After the existing Physical Inventory Conversion workflow has processed the staged images:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py complete <capture_session_id>
```

If processing fails:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py fail <capture_session_id> --message "reason"
```

## Runtime Paths

The desktop processor writes outside Git:

```text
<USERENVIRONMENT>/MobileCapture/Pending/
<USERENVIRONMENT>/MobileCapture/Processing/
<USERENVIRONMENT>/MobileCapture/Converted/
<USERENVIRONMENT>/MobileCapture/Failed/
<USERENVIRONMENT>/Capture/Physical_Inventory_Conversion/
```

Original uploaded images are retained in Supabase Storage and are also copied into the local processing folder when staged.

Storage object paths are scoped by operator user ID:

```text
mobile-capture-originals/{operator_user_id}/{etb_location}/{capture_session_id}/{sequence_number}-{image_id}.jpg
```
