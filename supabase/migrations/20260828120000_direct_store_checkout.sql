-- CardVector direct storefront checkout foundation.
--
-- CardUploader remains managed-inventory truth. These tables record direct
-- CardVector.app checkout attempts, paid orders, order items, and transactional
-- fulfillment state after Stripe Checkout validates customer payment.

create extension if not exists pgcrypto;

create table if not exists public.cardvector_direct_store_customers (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  normalized_email text generated always as (lower(trim(email))) stored,
  name text not null default '',
  stripe_customer_id text not null default '',
  marketing_opt_in boolean not null default false,
  marketing_consent_status text not null default 'unknown',
  marketing_consent_source text not null default '',
  marketing_consent_at timestamptz,
  first_order_at timestamptz,
  last_order_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cardvector_direct_store_customers_email_chk check (position('@' in email) > 1),
  constraint cardvector_direct_store_customers_marketing_chk check (
    marketing_consent_status in ('unknown', 'opt_in', 'opt_out', 'not_collected')
  )
);

create unique index if not exists cardvector_direct_store_customers_email_idx
  on public.cardvector_direct_store_customers(normalized_email);

create table if not exists public.cardvector_direct_store_orders (
  id uuid primary key default gen_random_uuid(),
  public_order_id text not null unique,
  order_status text not null default 'pending_payment',
  payment_status text not null default 'not_started',
  fulfillment_status text not null default 'not_ready',
  marketplace_release_status text not null default 'not_configured',
  currency text not null default 'USD',
  subtotal_cents integer not null default 0,
  shipping_cents integer not null default 0,
  tax_cents integer not null default 0,
  total_cents integer not null default 0,
  cart_hash text not null,
  inventory_snapshot_generated_at timestamptz,
  stripe_checkout_session_id text unique,
  stripe_payment_intent_id text not null default '',
  stripe_customer_id text not null default '',
  customer_id uuid references public.cardvector_direct_store_customers(id) on delete set null,
  customer_email text not null default '',
  customer_name text not null default '',
  shipping_address jsonb not null default '{}'::jsonb,
  billing_address jsonb not null default '{}'::jsonb,
  marketing_opt_in boolean not null default false,
  marketing_consent_status text not null default 'unknown',
  checkout_expires_at timestamptz,
  paid_at timestamptz,
  ready_to_ship_at timestamptz,
  shipped_at timestamptz,
  delivered_at timestamptz,
  tracking_number text not null default '',
  shipping_carrier text not null default '',
  shipping_confirmation_sent_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cardvector_direct_store_orders_status_chk check (
    order_status in ('pending_payment', 'paid', 'payment_failed', 'expired', 'cancelled', 'fulfilled', 'refunded')
  ),
  constraint cardvector_direct_store_orders_payment_chk check (
    payment_status in ('not_started', 'open', 'paid', 'failed', 'expired', 'refunded')
  ),
  constraint cardvector_direct_store_orders_fulfillment_chk check (
    fulfillment_status in ('not_ready', 'ready_to_ship', 'shipped', 'delivered', 'cancelled')
  ),
  constraint cardvector_direct_store_orders_release_chk check (
    marketplace_release_status in (
      'not_configured', 'pending_manual_review', 'manual_completed',
      'automation_pending', 'automation_completed', 'automation_failed'
    )
  ),
  constraint cardvector_direct_store_orders_marketing_chk check (
    marketing_consent_status in ('unknown', 'opt_in', 'opt_out', 'not_collected')
  ),
  constraint cardvector_direct_store_orders_amounts_chk check (
    subtotal_cents >= 0 and shipping_cents >= 0 and tax_cents >= 0 and total_cents >= 0
  )
);

create index if not exists cardvector_direct_store_orders_status_idx
  on public.cardvector_direct_store_orders(order_status, created_at desc);

create index if not exists cardvector_direct_store_orders_email_idx
  on public.cardvector_direct_store_orders(lower(customer_email), created_at desc)
  where customer_email <> '';

create table if not exists public.cardvector_direct_store_order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.cardvector_direct_store_orders(id) on delete cascade,
  item_id text not null,
  title text not null,
  game text not null default '',
  condition text not null default '',
  variant text not null default '',
  quantity integer not null,
  unit_price_cents integer not null,
  line_total_cents integer not null,
  source text not null default '',
  source_listing_id text not null default '',
  inventory_reference text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint cardvector_direct_store_order_items_quantity_chk check (quantity > 0),
  constraint cardvector_direct_store_order_items_amount_chk check (
    unit_price_cents > 0 and line_total_cents = quantity * unit_price_cents
  )
);

create unique index if not exists cardvector_direct_store_order_items_order_item_idx
  on public.cardvector_direct_store_order_items(order_id, item_id);

create table if not exists public.cardvector_direct_store_checkout_events (
  id uuid primary key default gen_random_uuid(),
  stripe_event_id text not null unique,
  event_type text not null,
  stripe_checkout_session_id text not null default '',
  order_id uuid references public.cardvector_direct_store_orders(id) on delete set null,
  processed_at timestamptz,
  processing_status text not null default 'received',
  error_message text not null default '',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cardvector_direct_store_checkout_events_status_chk check (
    processing_status in ('received', 'processed', 'ignored', 'failed')
  )
);

create index if not exists cardvector_direct_store_checkout_events_session_idx
  on public.cardvector_direct_store_checkout_events(stripe_checkout_session_id);

drop trigger if exists cardvector_direct_store_customers_touch_updated_at
  on public.cardvector_direct_store_customers;
create trigger cardvector_direct_store_customers_touch_updated_at
before update on public.cardvector_direct_store_customers
for each row execute function public.cardvector_registry_touch_updated_at();

drop trigger if exists cardvector_direct_store_orders_touch_updated_at
  on public.cardvector_direct_store_orders;
create trigger cardvector_direct_store_orders_touch_updated_at
before update on public.cardvector_direct_store_orders
for each row execute function public.cardvector_registry_touch_updated_at();

drop trigger if exists cardvector_direct_store_checkout_events_touch_updated_at
  on public.cardvector_direct_store_checkout_events;
create trigger cardvector_direct_store_checkout_events_touch_updated_at
before update on public.cardvector_direct_store_checkout_events
for each row execute function public.cardvector_registry_touch_updated_at();

alter table public.cardvector_direct_store_customers enable row level security;
alter table public.cardvector_direct_store_orders enable row level security;
alter table public.cardvector_direct_store_order_items enable row level security;
alter table public.cardvector_direct_store_checkout_events enable row level security;

revoke all on table public.cardvector_direct_store_customers from anon;
revoke all on table public.cardvector_direct_store_orders from anon;
revoke all on table public.cardvector_direct_store_order_items from anon;
revoke all on table public.cardvector_direct_store_checkout_events from anon;

revoke all on table public.cardvector_direct_store_customers from authenticated;
revoke all on table public.cardvector_direct_store_orders from authenticated;
revoke all on table public.cardvector_direct_store_order_items from authenticated;
revoke all on table public.cardvector_direct_store_checkout_events from authenticated;

grant select, insert, update on table public.cardvector_direct_store_customers to service_role;
grant select, insert, update on table public.cardvector_direct_store_orders to service_role;
grant select, insert on table public.cardvector_direct_store_order_items to service_role;
grant select, insert, update on table public.cardvector_direct_store_checkout_events to service_role;
