-- CardVector eBay active-listing reconciliation snapshots.
--
-- eBay remains the live marketplace listing source of truth. These tables store
-- authenticated CSV snapshots and operator review state only; they do not revise
-- or end live marketplace listings.

create table if not exists public.cardvector_marketplace_listing_snapshots (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  marketplace text not null default 'ebay',
  source text not null default 'ebay_active_listing_csv',
  source_file_name text not null default '',
  source_file_sha256 text not null default '',
  import_batch_id uuid not null default gen_random_uuid(),
  marketplace_listing_id text not null,
  sku text not null default '',
  listing_title text not null default '',
  listing_status text not null default 'active',
  current_price numeric(12, 2),
  currency text not null default 'USD',
  quantity_available integer,
  quantity_sold integer,
  condition text not null default '',
  category text not null default '',
  listing_url text not null default '',
  location_hint text not null default '',
  batch_sequence_label text not null default '',
  review_status text not null default 'needs_review',
  reason_codes text[] not null default '{}'::text[],
  raw_row jsonb not null default '{}'::jsonb,
  imported_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint cardvector_marketplace_listing_snapshots_marketplace_chk check (
    marketplace in ('ebay')
  ),
  constraint cardvector_marketplace_listing_snapshots_price_chk check (
    current_price is null or current_price >= 0
  ),
  constraint cardvector_marketplace_listing_snapshots_quantity_chk check (
    (quantity_available is null or quantity_available >= 0)
    and (quantity_sold is null or quantity_sold >= 0)
  ),
  constraint cardvector_marketplace_listing_snapshots_location_chk check (
    location_hint = ''
    or location_hint ~ '^ETB-[0-9]{3}-[A-J]$'
  ),
  constraint cardvector_marketplace_listing_snapshots_batch_label_chk check (
    batch_sequence_label = ''
    or batch_sequence_label ~ '^ETB-[0-9]{3}-[A-J](\.[0-9]+)?$'
  ),
  constraint cardvector_marketplace_listing_snapshots_review_status_chk check (
    review_status in (
      'location_linked',
      'needs_review',
      'missing_sku',
      'duplicate_sku',
      'duplicate_listing_id',
      'matched',
      'ignored'
    )
  )
);

create unique index if not exists cardvector_marketplace_listing_snapshots_identity_idx
  on public.cardvector_marketplace_listing_snapshots(owner_user_id, marketplace, marketplace_listing_id);

create index if not exists cardvector_marketplace_listing_snapshots_owner_import_idx
  on public.cardvector_marketplace_listing_snapshots(owner_user_id, imported_at desc);

create index if not exists cardvector_marketplace_listing_snapshots_sku_idx
  on public.cardvector_marketplace_listing_snapshots(owner_user_id, sku)
  where sku <> '';

create index if not exists cardvector_marketplace_listing_snapshots_location_idx
  on public.cardvector_marketplace_listing_snapshots(owner_user_id, location_hint)
  where location_hint <> '';

drop trigger if exists cardvector_marketplace_listing_snapshots_touch_updated_at
  on public.cardvector_marketplace_listing_snapshots;
create trigger cardvector_marketplace_listing_snapshots_touch_updated_at
before update on public.cardvector_marketplace_listing_snapshots
for each row execute function public.cardvector_registry_touch_updated_at();

alter table public.cardvector_marketplace_listing_snapshots enable row level security;

drop policy if exists "operators manage own eBay listing snapshots"
  on public.cardvector_marketplace_listing_snapshots;
create policy "operators manage own eBay listing snapshots"
  on public.cardvector_marketplace_listing_snapshots
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create table if not exists public.cardvector_inventory_listing_matches (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  marketplace_listing_snapshot_id uuid not null references public.cardvector_marketplace_listing_snapshots(id) on delete cascade,
  external_inventory_provider text not null default 'carduploader',
  external_inventory_id text not null default '',
  location_display_code text not null default '',
  batch_sequence_label text not null default '',
  match_status text not null default 'needs_review',
  match_confidence numeric(5, 4) not null default 0,
  reason_codes text[] not null default '{}'::text[],
  review_notes text not null default '',
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint cardvector_inventory_listing_matches_provider_chk check (
    external_inventory_provider in ('carduploader')
  ),
  constraint cardvector_inventory_listing_matches_confidence_chk check (
    match_confidence >= 0 and match_confidence <= 1
  ),
  constraint cardvector_inventory_listing_matches_location_chk check (
    location_display_code = ''
    or location_display_code ~ '^ETB-[0-9]{3}-[A-J]$'
  ),
  constraint cardvector_inventory_listing_matches_batch_label_chk check (
    batch_sequence_label = ''
    or batch_sequence_label ~ '^ETB-[0-9]{3}-[A-J](\.[0-9]+)?$'
  ),
  constraint cardvector_inventory_listing_matches_status_chk check (
    match_status in (
      'location_linked',
      'needs_review',
      'missing_sku',
      'duplicate_sku',
      'duplicate_listing_id',
      'matched',
      'ignored'
    )
  )
);

create unique index if not exists cardvector_inventory_listing_matches_snapshot_idx
  on public.cardvector_inventory_listing_matches(owner_user_id, marketplace_listing_snapshot_id);

create index if not exists cardvector_inventory_listing_matches_location_idx
  on public.cardvector_inventory_listing_matches(owner_user_id, location_display_code)
  where location_display_code <> '';

drop trigger if exists cardvector_inventory_listing_matches_touch_updated_at
  on public.cardvector_inventory_listing_matches;
create trigger cardvector_inventory_listing_matches_touch_updated_at
before update on public.cardvector_inventory_listing_matches
for each row execute function public.cardvector_registry_touch_updated_at();

alter table public.cardvector_inventory_listing_matches enable row level security;

drop policy if exists "operators manage own inventory listing matches"
  on public.cardvector_inventory_listing_matches;
create policy "operators manage own inventory listing matches"
  on public.cardvector_inventory_listing_matches
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create or replace view public.cardvector_ebay_listing_reconciliation_v
with (security_invoker = true) as
select
  snapshot.id,
  snapshot.owner_user_id,
  snapshot.marketplace,
  snapshot.marketplace_listing_id,
  snapshot.sku,
  snapshot.listing_title,
  snapshot.listing_status,
  snapshot.current_price,
  snapshot.currency,
  snapshot.quantity_available,
  snapshot.quantity_sold,
  snapshot.condition,
  snapshot.category,
  snapshot.listing_url,
  snapshot.location_hint,
  snapshot.batch_sequence_label,
  coalesce(match.match_status, snapshot.review_status) as review_status,
  coalesce(match.reason_codes, snapshot.reason_codes) as reason_codes,
  match.external_inventory_provider,
  match.external_inventory_id,
  match.match_confidence,
  snapshot.source_file_name,
  snapshot.source_file_sha256,
  snapshot.import_batch_id,
  snapshot.imported_at,
  snapshot.updated_at
from public.cardvector_marketplace_listing_snapshots snapshot
left join public.cardvector_inventory_listing_matches match
  on match.marketplace_listing_snapshot_id = snapshot.id
 and match.archived_at is null
where snapshot.archived_at is null;

revoke all on table public.cardvector_marketplace_listing_snapshots from anon;
revoke all on table public.cardvector_inventory_listing_matches from anon;
revoke all on table public.cardvector_ebay_listing_reconciliation_v from anon;

grant select, insert, update on table public.cardvector_marketplace_listing_snapshots
  to authenticated;

grant select, insert, update on table public.cardvector_inventory_listing_matches
  to authenticated;

grant select on table public.cardvector_ebay_listing_reconciliation_v
  to authenticated;

grant select, insert, update on table public.cardvector_marketplace_listing_snapshots
  to service_role;

grant select, insert, update on table public.cardvector_inventory_listing_matches
  to service_role;

grant select on table public.cardvector_ebay_listing_reconciliation_v
  to service_role;

notify pgrst, 'reload schema';
