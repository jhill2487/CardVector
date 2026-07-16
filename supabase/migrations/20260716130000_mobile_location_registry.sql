-- CardVector Mobile ETB/location identity and secure next-location creation.
--
-- Supabase is authoritative for cloud-visible ETB/location identity. The
-- desktop JSON registry remains the offline operational projection for counts,
-- statuses, batches, labels, and capture workflows.

create table if not exists public.cardvector_location_operators (
  user_id uuid primary key references auth.users(id) on delete cascade,
  can_manage_locations boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.cardvector_etbs (
  etb_id text primary key,
  status text not null default 'Empty',
  capacity integer not null default 400,
  active_location_code text,
  source_updated_at text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cardvector_etbs_id_chk check (etb_id ~ '^ETB-[0-9]{3}$'),
  constraint cardvector_etbs_status_chk check (status in ('Empty', 'Active', 'Full', 'Needs Review', 'Archived')),
  constraint cardvector_etbs_capacity_chk check (capacity > 0),
  constraint cardvector_etbs_active_location_chk check (active_location_code is null or active_location_code ~ '^[A-J]$')
);

create table if not exists public.cardvector_locations (
  location_id text primary key,
  etb_id text not null references public.cardvector_etbs(etb_id) on delete restrict,
  location_code text not null,
  status text not null default 'Empty',
  capacity integer not null default 40,
  stored_count integer not null default 0,
  assigned_batch text not null default '',
  source_updated_at text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cardvector_locations_code_chk check (location_code ~ '^[A-J]$'),
  constraint cardvector_locations_id_chk check (location_id = etb_id || '-' || location_code),
  constraint cardvector_locations_status_chk check (status in ('Empty', 'Active', 'Full', 'Location Complete', 'Needs Review', 'Archived')),
  constraint cardvector_locations_capacity_chk check (capacity > 0),
  constraint cardvector_locations_stored_count_chk check (stored_count >= 0 and stored_count <= capacity),
  constraint cardvector_locations_etb_code_unique unique (etb_id, location_code)
);

create index if not exists cardvector_locations_etb_idx
  on public.cardvector_locations(etb_id, location_code);

drop trigger if exists cardvector_location_operators_touch_updated_at on public.cardvector_location_operators;
create trigger cardvector_location_operators_touch_updated_at
before update on public.cardvector_location_operators
for each row execute function public.cardvector_mobile_capture_touch_updated_at();

drop trigger if exists cardvector_etbs_touch_updated_at on public.cardvector_etbs;
create trigger cardvector_etbs_touch_updated_at
before update on public.cardvector_etbs
for each row execute function public.cardvector_mobile_capture_touch_updated_at();

drop trigger if exists cardvector_locations_touch_updated_at on public.cardvector_locations;
create trigger cardvector_locations_touch_updated_at
before update on public.cardvector_locations
for each row execute function public.cardvector_mobile_capture_touch_updated_at();

alter table public.cardvector_location_operators enable row level security;
alter table public.cardvector_etbs enable row level security;
alter table public.cardvector_locations enable row level security;

drop policy if exists "operators read own location authorization" on public.cardvector_location_operators;
drop policy if exists "authorized operators read etbs" on public.cardvector_etbs;
drop policy if exists "authorized operators read locations" on public.cardvector_locations;

create policy "operators read own location authorization"
  on public.cardvector_location_operators
  for select
  to authenticated
  using (user_id = auth.uid());

create policy "authorized operators read etbs"
  on public.cardvector_etbs
  for select
  to authenticated
  using (
    exists (
      select 1
        from public.cardvector_location_operators operator_access
       where operator_access.user_id = auth.uid()
         and operator_access.can_manage_locations
    )
  );

create policy "authorized operators read locations"
  on public.cardvector_locations
  for select
  to authenticated
  using (
    exists (
      select 1
        from public.cardvector_location_operators operator_access
       where operator_access.user_id = auth.uid()
         and operator_access.can_manage_locations
    )
  );

revoke all on table public.cardvector_location_operators from anon;
revoke all on table public.cardvector_etbs from anon;
revoke all on table public.cardvector_locations from anon;

revoke insert, update, delete on table public.cardvector_location_operators from authenticated;
revoke insert, update, delete on table public.cardvector_etbs from authenticated;
revoke insert, update, delete on table public.cardvector_locations from authenticated;

grant select on table public.cardvector_location_operators to authenticated;
grant select on table public.cardvector_etbs to authenticated;
grant select on table public.cardvector_locations to authenticated;

grant select, insert, update on table public.cardvector_location_operators to service_role;
grant select, insert, update on table public.cardvector_etbs to service_role;
grant select, insert, update on table public.cardvector_locations to service_role;

create or replace function public.cardvector_create_next_location(
  p_etb_id text,
  p_expected_location_code text default null
)
returns table (
  location_id text,
  etb_id text,
  location_code text,
  status text,
  capacity integer,
  stored_count integer,
  assigned_batch text,
  created_at timestamptz,
  updated_at timestamptz
)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_user_id uuid := auth.uid();
  v_etb_id text := upper(btrim(coalesce(p_etb_id, '')));
  v_expected text := upper(btrim(coalesce(p_expected_location_code, '')));
  v_locked_etb text;
  v_next_code text;
  v_created public.cardvector_locations%rowtype;
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

  if v_etb_id !~ '^ETB-[0-9]{3}$' then
    raise exception using errcode = '22023', message = 'ETB ID must use ETB-### format.';
  end if;

  if v_expected <> '' and v_expected !~ '^[A-J]$' then
    raise exception using errcode = '22023', message = 'Expected location code must be A-J.';
  end if;

  select etb.etb_id
    into v_locked_etb
    from public.cardvector_etbs etb
   where etb.etb_id = v_etb_id
   for update;

  if v_locked_etb is null then
    raise exception using errcode = 'P0002', message = 'ETB not found.';
  end if;

  select allowed.location_code
    into v_next_code
    from unnest(array['A','B','C','D','E','F','G','H','I','J'])
         with ordinality as allowed(location_code, sequence_number)
   where not exists (
     select 1
       from public.cardvector_locations existing
      where existing.etb_id = v_etb_id
        and existing.location_code = allowed.location_code
   )
   order by allowed.sequence_number
   limit 1;

  if v_next_code is null then
    raise exception using errcode = '23514', message = 'No available location remains for this ETB.';
  end if;

  if v_expected <> '' and v_expected <> v_next_code then
    raise exception using errcode = '40001', message = 'Location availability changed. Refresh and confirm the new proposal.';
  end if;

  insert into public.cardvector_locations (
    location_id,
    etb_id,
    location_code,
    status,
    capacity,
    stored_count,
    assigned_batch,
    created_by
  ) values (
    v_etb_id || '-' || v_next_code,
    v_etb_id,
    v_next_code,
    'Empty',
    40,
    0,
    '',
    v_user_id
  )
  returning * into v_created;

  return query
  select
    v_created.location_id,
    v_created.etb_id,
    v_created.location_code,
    v_created.status,
    v_created.capacity,
    v_created.stored_count,
    v_created.assigned_batch,
    v_created.created_at,
    v_created.updated_at;
end;
$$;

revoke all on function public.cardvector_create_next_location(text, text) from public;
revoke all on function public.cardvector_create_next_location(text, text) from anon;
grant execute on function public.cardvector_create_next_location(text, text) to authenticated;

-- Production activation is intentionally explicit. After applying this
-- migration, authorize the CardVector operator from the Supabase SQL editor:
--
-- insert into public.cardvector_location_operators (user_id, can_manage_locations)
-- values ('<AUTH_USER_UUID>', true)
-- on conflict (user_id) do update set can_manage_locations = excluded.can_manage_locations;
