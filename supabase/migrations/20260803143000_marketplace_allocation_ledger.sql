-- CardVector marketplace allocation ledger groundwork.
--
-- This extends the existing read-only listing snapshot workflow so CardVector.app
-- can compare eBay and TCGplayer listed quantities against imported
-- CardUploader inventory evidence before any live marketplace sync exists.

alter table public.cardvector_marketplace_listing_snapshots
  drop constraint if exists cardvector_marketplace_listing_snapshots_marketplace_chk;

alter table public.cardvector_marketplace_listing_snapshots
  add constraint cardvector_marketplace_listing_snapshots_marketplace_chk check (
    marketplace in ('ebay', 'tcgplayer')
  );

create table if not exists public.cardvector_inventory_quantity_snapshots (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  external_inventory_provider text not null default 'carduploader',
  source text not null default 'carduploader_inventory_csv',
  source_file_name text not null default '',
  source_file_sha256 text not null default '',
  import_batch_id uuid not null default gen_random_uuid(),
  external_inventory_id text not null default '',
  sku text not null default '',
  inventory_title text not null default '',
  inventory_status text not null default '',
  condition text not null default '',
  location_display_code text not null default '',
  physical_quantity integer,
  available_quantity integer,
  reserved_quantity integer,
  sold_quantity integer,
  raw_row jsonb not null default '{}'::jsonb,
  imported_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint cardvector_inventory_quantity_snapshots_provider_chk check (
    external_inventory_provider in ('carduploader', 'manual_snapshot')
  ),
  constraint cardvector_inventory_quantity_snapshots_quantity_chk check (
    (physical_quantity is null or physical_quantity >= 0)
    and (available_quantity is null or available_quantity >= 0)
    and (reserved_quantity is null or reserved_quantity >= 0)
    and (sold_quantity is null or sold_quantity >= 0)
  ),
  constraint cardvector_inventory_quantity_snapshots_location_chk check (
    location_display_code = ''
    or location_display_code ~ '^ETB-[0-9]{3}-[A-J](\.[0-9]+)?$'
  )
);

comment on table public.cardvector_inventory_quantity_snapshots is
  'Read-only imported inventory evidence. CardUploader remains canonical inventory truth.';

create unique index if not exists cardvector_inventory_quantity_snapshots_identity_idx
  on public.cardvector_inventory_quantity_snapshots(
    owner_user_id,
    external_inventory_provider,
    external_inventory_id,
    condition
  );

create index if not exists cardvector_inventory_quantity_snapshots_owner_import_idx
  on public.cardvector_inventory_quantity_snapshots(owner_user_id, imported_at desc);

create index if not exists cardvector_inventory_quantity_snapshots_sku_idx
  on public.cardvector_inventory_quantity_snapshots(owner_user_id, sku)
  where sku <> '';

drop trigger if exists cardvector_inventory_quantity_snapshots_touch_updated_at
  on public.cardvector_inventory_quantity_snapshots;
create trigger cardvector_inventory_quantity_snapshots_touch_updated_at
before update on public.cardvector_inventory_quantity_snapshots
for each row execute function public.cardvector_registry_touch_updated_at();

alter table public.cardvector_inventory_quantity_snapshots enable row level security;

drop policy if exists "operators manage own inventory quantity snapshots"
  on public.cardvector_inventory_quantity_snapshots;
create policy "operators manage own inventory quantity snapshots"
  on public.cardvector_inventory_quantity_snapshots
  for all
  to authenticated
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create or replace view public.cardvector_marketplace_listing_reconciliation_v
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
  snapshot.source,
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

create or replace view public.cardvector_marketplace_allocation_ledger_v
with (security_invoker = true) as
with marketplace_quantities as (
  select
    owner_user_id,
    sku,
    sum(coalesce(quantity_available, 0)) filter (where marketplace = 'ebay') as ebay_listed_quantity,
    sum(coalesce(quantity_available, 0)) filter (where marketplace = 'tcgplayer') as tcgplayer_listed_quantity,
    sum(coalesce(quantity_available, 0)) as total_listed_quantity,
    array_agg(distinct marketplace order by marketplace) as listed_marketplaces,
    max(imported_at) as last_marketplace_import_at
  from public.cardvector_marketplace_listing_snapshots
  where archived_at is null
    and sku <> ''
  group by owner_user_id, sku
),
latest_inventory as (
  select distinct on (owner_user_id, sku)
    owner_user_id,
    sku,
    inventory_title,
    physical_quantity,
    available_quantity,
    reserved_quantity,
    sold_quantity,
    imported_at as last_inventory_import_at
  from public.cardvector_inventory_quantity_snapshots
  where archived_at is null
    and sku <> ''
  order by owner_user_id, sku, imported_at desc, updated_at desc
)
select
  mq.owner_user_id,
  mq.sku,
  coalesce(inv.inventory_title, '') as inventory_title,
  inv.physical_quantity,
  inv.available_quantity,
  coalesce(mq.ebay_listed_quantity, 0)::integer as ebay_listed_quantity,
  coalesce(mq.tcgplayer_listed_quantity, 0)::integer as tcgplayer_listed_quantity,
  coalesce(mq.total_listed_quantity, 0)::integer as total_listed_quantity,
  mq.listed_marketplaces,
  case
    when inv.available_quantity is null then 'needs_inventory_snapshot'
    when coalesce(mq.total_listed_quantity, 0) > inv.available_quantity then 'oversell_risk'
    when coalesce(mq.ebay_listed_quantity, 0) > 0
      and coalesce(mq.tcgplayer_listed_quantity, 0) > 0
      and inv.available_quantity <= greatest(coalesce(mq.ebay_listed_quantity, 0), coalesce(mq.tcgplayer_listed_quantity, 0))
      then 'cross_channel_conflict'
    when coalesce(mq.total_listed_quantity, 0) = inv.available_quantity then 'fully_allocated'
    when coalesce(mq.total_listed_quantity, 0) < inv.available_quantity then 'safe_capacity'
    else 'needs_review'
  end as allocation_status,
  case
    when inv.available_quantity is null then array['NEEDS_CARDUPLOADER_INVENTORY_SNAPSHOT']::text[]
    when coalesce(mq.total_listed_quantity, 0) > inv.available_quantity then array['LISTED_QUANTITY_EXCEEDS_AVAILABLE']::text[]
    when coalesce(mq.ebay_listed_quantity, 0) > 0
      and coalesce(mq.tcgplayer_listed_quantity, 0) > 0
      and inv.available_quantity <= greatest(coalesce(mq.ebay_listed_quantity, 0), coalesce(mq.tcgplayer_listed_quantity, 0))
      then array['MULTIPLE_MARKETPLACES_SHARE_SINGLE_CAPACITY']::text[]
    when coalesce(mq.total_listed_quantity, 0) = inv.available_quantity then array['LISTED_QUANTITY_EQUALS_AVAILABLE']::text[]
    when coalesce(mq.total_listed_quantity, 0) < inv.available_quantity then array['AVAILABLE_QUANTITY_REMAINS']::text[]
    else array['ALLOCATION_REVIEW_REQUIRED']::text[]
  end as reason_codes,
  mq.last_marketplace_import_at,
  inv.last_inventory_import_at
from marketplace_quantities mq
left join latest_inventory inv
  on inv.owner_user_id = mq.owner_user_id
 and inv.sku = mq.sku;

revoke all on table public.cardvector_inventory_quantity_snapshots from anon;
revoke all on table public.cardvector_marketplace_listing_reconciliation_v from anon;
revoke all on table public.cardvector_marketplace_allocation_ledger_v from anon;

grant select, insert, update on table public.cardvector_inventory_quantity_snapshots
  to authenticated;

grant select on table public.cardvector_marketplace_listing_reconciliation_v
  to authenticated;

grant select on table public.cardvector_marketplace_allocation_ledger_v
  to authenticated;

grant select, insert, update on table public.cardvector_inventory_quantity_snapshots
  to service_role;

grant select on table public.cardvector_marketplace_listing_reconciliation_v
  to service_role;

grant select on table public.cardvector_marketplace_allocation_ledger_v
  to service_role;

notify pgrst, 'reload schema';
