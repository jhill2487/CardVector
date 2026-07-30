-- CardVector CardUploader batch-event references.
--
-- CardUploader remains the managed inventory source of truth. This table only
-- records historical CardUploader batch webpage references and their
-- relationship to canonical CardVector ETB/location records.

create table if not exists public.cardvector_carduploader_batch_events (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid references auth.users(id) on delete set null,
  organization_id text,
  location_id uuid references public.cardvector_storage_locations(id) on delete set null,
  location_display_code text,
  etb_display_code text,
  carduploader_batch_id text not null,
  carduploader_batch_url text not null,
  carduploader_batch_name text not null default '',
  batch_label text not null default '',
  batch_type text not null default 'ungraded',
  game text not null default '',
  language text not null default '',
  event_type text not null default 'unknown',
  card_count integer,
  total_value numeric(12, 2),
  batch_date date,
  source text not null default 'carduploader_history_scrape',
  scraped_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  migration_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint cardvector_carduploader_batch_events_url_chk check (
    carduploader_batch_url ~ '^https://carduploader\.com/dashboard/history/'
  ),
  constraint cardvector_carduploader_batch_events_count_chk check (
    card_count is null or card_count >= 0
  ),
  constraint cardvector_carduploader_batch_events_type_chk check (
    event_type in ('initial_fill', 'refill', 'correction', 'unassigned', 'unknown')
  ),
  constraint cardvector_carduploader_batch_events_location_chk check (
    location_display_code is null
    or location_display_code ~ '^ETB-[0-9]{3}-[A-J]$'
  ),
  constraint cardvector_carduploader_batch_events_etb_chk check (
    etb_display_code is null
    or etb_display_code ~ '^ETB-[0-9]{3}$'
  )
);

create unique index if not exists cardvector_carduploader_batch_events_batch_id_idx
  on public.cardvector_carduploader_batch_events(carduploader_batch_id)
  where archived_at is null;

create index if not exists cardvector_carduploader_batch_events_location_idx
  on public.cardvector_carduploader_batch_events(location_id, batch_date);

create index if not exists cardvector_carduploader_batch_events_location_code_idx
  on public.cardvector_carduploader_batch_events(location_display_code, batch_date);

create index if not exists cardvector_carduploader_batch_events_owner_idx
  on public.cardvector_carduploader_batch_events(owner_user_id, batch_date);

drop trigger if exists cardvector_carduploader_batch_events_touch_updated_at
  on public.cardvector_carduploader_batch_events;
create trigger cardvector_carduploader_batch_events_touch_updated_at
before update on public.cardvector_carduploader_batch_events
for each row execute function public.cardvector_registry_touch_updated_at();

alter table public.cardvector_carduploader_batch_events enable row level security;

drop policy if exists "operators manage own carduploader batch events"
  on public.cardvector_carduploader_batch_events;
create policy "operators manage own carduploader batch events"
  on public.cardvector_carduploader_batch_events
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

drop policy if exists "authorized operators read carduploader batch events"
  on public.cardvector_carduploader_batch_events;
create policy "authorized operators read carduploader batch events"
  on public.cardvector_carduploader_batch_events
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

revoke all on table public.cardvector_carduploader_batch_events from anon;

grant select, insert, update on table public.cardvector_carduploader_batch_events
  to authenticated;

grant select, insert, update on table public.cardvector_carduploader_batch_events
  to service_role;

create or replace view public.cardvector_location_carduploader_batches_v as
select
  event.id,
  event.location_id,
  location.display_code as canonical_location_display_code,
  event.location_display_code,
  event.etb_display_code,
  event.carduploader_batch_id,
  event.carduploader_batch_url,
  event.carduploader_batch_name,
  event.batch_label,
  event.batch_type,
  event.game,
  event.language,
  event.event_type,
  event.card_count,
  event.total_value,
  event.batch_date,
  event.source,
  event.scraped_at,
  event.created_at,
  event.updated_at
from public.cardvector_carduploader_batch_events event
left join public.cardvector_storage_locations location
  on location.id = event.location_id
where event.archived_at is null;
