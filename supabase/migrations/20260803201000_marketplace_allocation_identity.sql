-- Refine marketplace allocation identity for CardUploader-managed inventory.
--
-- CardUploader-managed inventory separates:
-- - Catalog SKU (CS-*) used by marketplace listings for grouped products.
-- - User SKU / ETB code used as physical storage-location evidence.
--
-- The allocation ledger must reconcile marketplace quantities against the
-- CardUploader catalog SKU and classify non-CS marketplace rows as legacy
-- listing evidence rather than missing CardUploader snapshots.

create or replace view public.cardvector_marketplace_allocation_ledger_v
with (security_invoker = true) as
with marketplace_lines as (
  select
    owner_user_id,
    marketplace,
    marketplace_listing_id,
    listing_title,
    quantity_available,
    imported_at,
    case
      when btrim(coalesce(sku, '')) <> '' then upper(btrim(sku))
      else upper(btrim(marketplace || ':' || marketplace_listing_id))
    end as allocation_key,
    case
      when btrim(coalesce(sku, '')) = '' then 'marketplace_listing_id'
      when upper(btrim(sku)) like 'CS-%' then 'carduploader_catalog_sku'
      else 'legacy_marketplace_sku'
    end as allocation_key_type
  from public.cardvector_marketplace_listing_snapshots
  where archived_at is null
    and marketplace_listing_id <> ''
),
marketplace_quantities as (
  select
    owner_user_id,
    allocation_key,
    max(allocation_key_type) as allocation_key_type,
    max(listing_title) as sample_listing_title,
    sum(coalesce(quantity_available, 0)) filter (where marketplace = 'ebay') as ebay_listed_quantity,
    sum(coalesce(quantity_available, 0)) filter (where marketplace = 'tcgplayer') as tcgplayer_listed_quantity,
    sum(coalesce(quantity_available, 0)) as total_listed_quantity,
    array_agg(distinct marketplace order by marketplace) as listed_marketplaces,
    max(imported_at) as last_marketplace_import_at
  from marketplace_lines
  group by owner_user_id, allocation_key
),
latest_inventory_batches as (
  select distinct on (owner_user_id, external_inventory_provider)
    owner_user_id,
    external_inventory_provider,
    import_batch_id
  from public.cardvector_inventory_quantity_snapshots
  where archived_at is null
    and external_inventory_provider = 'carduploader'
  order by owner_user_id, external_inventory_provider, imported_at desc, updated_at desc
),
latest_inventory_records as (
  select distinct on (
    inv.owner_user_id,
    inv.external_inventory_provider,
    inv.external_inventory_id,
    inv.condition
  )
    inv.*
  from public.cardvector_inventory_quantity_snapshots inv
  join latest_inventory_batches batch
    on batch.owner_user_id = inv.owner_user_id
   and batch.external_inventory_provider = inv.external_inventory_provider
   and batch.import_batch_id = inv.import_batch_id
  where inv.archived_at is null
  order by
    inv.owner_user_id,
    inv.external_inventory_provider,
    inv.external_inventory_id,
    inv.condition,
    inv.imported_at desc,
    inv.updated_at desc
),
inventory_lines as (
  select
    owner_user_id,
    upper(btrim(coalesce(
      nullif(raw_row ->> 'Catalog SKU', ''),
      nullif(raw_row #>> '{canonical_row,Catalog SKU}', ''),
      nullif(sku, '')
    ))) as catalog_sku,
    inventory_title,
    lower(btrim(coalesce(inventory_status, ''))) as inventory_status,
    coalesce(physical_quantity, available_quantity, 0) as physical_quantity,
    case
      when lower(btrim(coalesce(inventory_status, ''))) in ('sold', 'removed', 'deleted', 'archived') then 0
      else coalesce(available_quantity, physical_quantity, 0)
    end as available_quantity,
    imported_at
  from latest_inventory_records
),
inventory_quantities as (
  select
    owner_user_id,
    catalog_sku,
    max(inventory_title) as inventory_title,
    sum(physical_quantity)::integer as physical_quantity,
    sum(available_quantity)::integer as available_quantity,
    max(imported_at) as last_inventory_import_at
  from inventory_lines
  where catalog_sku <> ''
  group by owner_user_id, catalog_sku
)
select
  mq.owner_user_id,
  mq.allocation_key as sku,
  coalesce(inv.inventory_title, mq.sample_listing_title, '') as inventory_title,
  inv.physical_quantity,
  inv.available_quantity,
  coalesce(mq.ebay_listed_quantity, 0)::integer as ebay_listed_quantity,
  coalesce(mq.tcgplayer_listed_quantity, 0)::integer as tcgplayer_listed_quantity,
  coalesce(mq.total_listed_quantity, 0)::integer as total_listed_quantity,
  mq.listed_marketplaces,
  case
    when inv.available_quantity is null
      and mq.allocation_key_type = 'carduploader_catalog_sku'
      then 'needs_inventory_snapshot'
    when inv.available_quantity is null
      and coalesce(mq.ebay_listed_quantity, 0) > 0
      and coalesce(mq.tcgplayer_listed_quantity, 0) = 0
      then 'ebay_only_legacy_listing'
    when inv.available_quantity is null
      then 'marketplace_only_legacy_listing'
    when coalesce(mq.total_listed_quantity, 0) > inv.available_quantity
      then 'oversell_risk'
    when coalesce(mq.ebay_listed_quantity, 0) > 0
      and coalesce(mq.tcgplayer_listed_quantity, 0) > 0
      and inv.available_quantity <= greatest(coalesce(mq.ebay_listed_quantity, 0), coalesce(mq.tcgplayer_listed_quantity, 0))
      then 'cross_channel_conflict'
    when coalesce(mq.total_listed_quantity, 0) = inv.available_quantity
      then 'fully_allocated'
    when coalesce(mq.total_listed_quantity, 0) < inv.available_quantity
      then 'safe_capacity'
    else 'needs_review'
  end as allocation_status,
  case
    when inv.available_quantity is null
      and mq.allocation_key_type = 'carduploader_catalog_sku'
      then array['NEEDS_CARDUPLOADER_INVENTORY_SNAPSHOT']::text[]
    when inv.available_quantity is null
      and coalesce(mq.ebay_listed_quantity, 0) > 0
      and coalesce(mq.tcgplayer_listed_quantity, 0) = 0
      then array['EBAY_LISTING_NOT_LINKED_TO_CARDUPLOADER_CATALOG_SKU']::text[]
    when inv.available_quantity is null
      then array['MARKETPLACE_LISTING_NOT_LINKED_TO_CARDUPLOADER_CATALOG_SKU']::text[]
    when coalesce(mq.total_listed_quantity, 0) > inv.available_quantity
      then array['LISTED_QUANTITY_EXCEEDS_AVAILABLE']::text[]
    when coalesce(mq.ebay_listed_quantity, 0) > 0
      and coalesce(mq.tcgplayer_listed_quantity, 0) > 0
      and inv.available_quantity <= greatest(coalesce(mq.ebay_listed_quantity, 0), coalesce(mq.tcgplayer_listed_quantity, 0))
      then array['MULTIPLE_MARKETPLACES_SHARE_SINGLE_CAPACITY']::text[]
    when coalesce(mq.total_listed_quantity, 0) = inv.available_quantity
      then array['LISTED_QUANTITY_EQUALS_AVAILABLE']::text[]
    when coalesce(mq.total_listed_quantity, 0) < inv.available_quantity
      then array['AVAILABLE_QUANTITY_REMAINS']::text[]
    else array['ALLOCATION_REVIEW_REQUIRED']::text[]
  end as reason_codes,
  mq.last_marketplace_import_at,
  inv.last_inventory_import_at
from marketplace_quantities mq
left join inventory_quantities inv
  on inv.owner_user_id = mq.owner_user_id
 and inv.catalog_sku = mq.allocation_key;

grant select on table public.cardvector_marketplace_allocation_ledger_v
  to authenticated;

grant select on table public.cardvector_marketplace_allocation_ledger_v
  to service_role;

notify pgrst, 'reload schema';
