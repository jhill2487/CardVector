-- CardVector direct storefront release-job queue.
--
-- Paid CardVector.app direct-store orders enqueue private jobs for the
-- CardUploader/eBay release workflow. This table is intentionally service-role
-- only until the trusted PC helper/executor is wired and tested.

create table if not exists public.cardvector_direct_store_release_jobs (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.cardvector_direct_store_orders(id) on delete cascade,
  order_item_id uuid not null references public.cardvector_direct_store_order_items(id) on delete cascade,
  public_order_id text not null,
  target_system text not null default 'carduploader',
  target_marketplace text not null default 'ebay',
  release_action text not null default 'release_purchased_quantity',
  release_status text not null default 'pending',
  item_id text not null,
  title text not null,
  quantity integer not null,
  source text not null default '',
  source_listing_id text not null default '',
  inventory_reference text not null default '',
  claimed_by text not null default '',
  claimed_at timestamptz,
  completed_at timestamptz,
  attempt_count integer not null default 0,
  last_error text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cardvector_direct_store_release_jobs_quantity_chk check (quantity > 0),
  constraint cardvector_direct_store_release_jobs_target_system_chk check (
    target_system in ('carduploader')
  ),
  constraint cardvector_direct_store_release_jobs_target_marketplace_chk check (
    target_marketplace in ('ebay')
  ),
  constraint cardvector_direct_store_release_jobs_action_chk check (
    release_action in ('release_purchased_quantity')
  ),
  constraint cardvector_direct_store_release_jobs_status_chk check (
    release_status in ('pending', 'claimed', 'completed', 'failed', 'manual_review', 'cancelled')
  ),
  constraint cardvector_direct_store_release_jobs_attempts_chk check (attempt_count >= 0)
);

create unique index if not exists cardvector_direct_store_release_jobs_order_item_idx
  on public.cardvector_direct_store_release_jobs(order_item_id);

create index if not exists cardvector_direct_store_release_jobs_status_idx
  on public.cardvector_direct_store_release_jobs(release_status, created_at);

create index if not exists cardvector_direct_store_release_jobs_order_idx
  on public.cardvector_direct_store_release_jobs(order_id);

drop trigger if exists cardvector_direct_store_release_jobs_touch_updated_at
  on public.cardvector_direct_store_release_jobs;
create trigger cardvector_direct_store_release_jobs_touch_updated_at
before update on public.cardvector_direct_store_release_jobs
for each row execute function public.cardvector_direct_store_touch_updated_at();

alter table public.cardvector_direct_store_release_jobs enable row level security;

revoke all on table public.cardvector_direct_store_release_jobs from anon;
revoke all on table public.cardvector_direct_store_release_jobs from authenticated;

grant select, insert, update on table public.cardvector_direct_store_release_jobs to service_role;
