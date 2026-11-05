-- CardVector marketplace foundation (new namespace; no legacy tables modified).
-- Apply only after review. Auth users are managed by Supabase Auth.
create table public.cv_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '' check (char_length(display_name) <= 80),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table public.cv_want_lists (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 100),
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id)
);
create unique index cv_one_default_list_per_user on public.cv_want_lists(owner_id) where is_default;
create index cv_want_lists_owner_idx on public.cv_want_lists(owner_id);

create table public.cv_want_list_items (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  list_id uuid not null,
  catalog_source text not null check (char_length(trim(catalog_source)) between 1 and 60),
  external_card_id text not null check (char_length(trim(external_card_id)) between 1 and 160),
  card_name text not null check (char_length(trim(card_name)) between 1 and 160),
  set_name text not null default '',
  card_number text not null default '',
  language text not null default 'en',
  printing text not null default '',
  variant text not null default '',
  minimum_condition text not null default 'LP' check (minimum_condition in ('NM','LP')),
  priority smallint not null default 2 check (priority between 1 and 3),
  quantity integer not null default 1 check (quantity between 1 and 100),
  created_at timestamptz not null default now(),
  foreign key (list_id,owner_id) references public.cv_want_lists(id,owner_id) on delete cascade,
  unique (id,owner_id)
);
create index cv_want_list_items_list_idx on public.cv_want_list_items(list_id);
create index cv_want_list_items_card_idx on public.cv_want_list_items(catalog_source,external_card_id);

create table public.cv_seller_applications (
  user_id uuid primary key references auth.users(id) on delete cascade,
  business_name text not null default '',
  note text not null default '' check (char_length(note) <= 2000),
  status text not null default 'pending' check (status in ('pending','approved','rejected','suspended')),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  check (char_length(business_name) <= 160)
);
-- Seller approval is server/admin-only. Client inserts must not set status.

create table public.cv_sourcing_requests (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'active' check (status in ('active','paused','cancelled','fulfilled')),
  total_budget_cents integer check (total_budget_cents is null or total_budget_cents >= 0),
  bundle_preference text not null default 'flexible' check (bundle_preference in ('flexible','bundle_only')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(id,owner_id)
);
create index cv_sourcing_requests_owner_idx on public.cv_sourcing_requests(owner_id,status);

create table public.cv_sourcing_request_items (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  request_id uuid not null,
  want_item_id uuid not null,
  requested_quantity integer not null default 1 check (requested_quantity between 1 and 100),
  max_unit_price_cents integer check (max_unit_price_cents is null or max_unit_price_cents >= 0),
  foreign key(request_id,owner_id) references public.cv_sourcing_requests(id,owner_id) on delete cascade,
  foreign key(want_item_id,owner_id) references public.cv_want_list_items(id,owner_id) on delete restrict,
  unique(request_id,want_item_id)
);
create index cv_sourcing_request_items_request_idx on public.cv_sourcing_request_items(request_id);

alter table public.cv_profiles enable row level security;
alter table public.cv_want_lists enable row level security;
alter table public.cv_want_list_items enable row level security;
alter table public.cv_seller_applications enable row level security;
alter table public.cv_sourcing_requests enable row level security;
alter table public.cv_sourcing_request_items enable row level security;

create policy cv_profiles_select on public.cv_profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy cv_profiles_insert on public.cv_profiles for insert to authenticated with check ((select auth.uid()) = user_id);
create policy cv_profiles_update on public.cv_profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

create policy cv_want_lists_select on public.cv_want_lists for select to authenticated using ((select auth.uid()) = owner_id);
create policy cv_want_lists_insert on public.cv_want_lists for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy cv_want_lists_update on public.cv_want_lists for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy cv_want_lists_delete on public.cv_want_lists for delete to authenticated using ((select auth.uid()) = owner_id);

create policy cv_want_items_select on public.cv_want_list_items for select to authenticated using ((select auth.uid()) = owner_id);
create policy cv_want_items_insert on public.cv_want_list_items for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy cv_want_items_update on public.cv_want_list_items for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy cv_want_items_delete on public.cv_want_list_items for delete to authenticated using ((select auth.uid()) = owner_id);

create policy cv_seller_applications_select on public.cv_seller_applications for select to authenticated using ((select auth.uid()) = user_id);
create policy cv_seller_applications_insert on public.cv_seller_applications for insert to authenticated with check ((select auth.uid()) = user_id and status = 'pending' and reviewed_at is null);
-- No client update policy: approval/rejection must be done by a trusted admin process.

create policy cv_requests_select on public.cv_sourcing_requests for select to authenticated using ((select auth.uid()) = owner_id);
create policy cv_requests_insert on public.cv_sourcing_requests for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy cv_requests_update on public.cv_sourcing_requests for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy cv_requests_delete on public.cv_sourcing_requests for delete to authenticated using ((select auth.uid()) = owner_id);

create policy cv_request_items_select on public.cv_sourcing_request_items for select to authenticated using ((select auth.uid()) = owner_id);
create policy cv_request_items_insert on public.cv_sourcing_request_items for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy cv_request_items_update on public.cv_sourcing_request_items for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy cv_request_items_delete on public.cv_sourcing_request_items for delete to authenticated using ((select auth.uid()) = owner_id);

revoke all on public.cv_profiles,public.cv_want_lists,public.cv_want_list_items,public.cv_seller_applications,public.cv_sourcing_requests,public.cv_sourcing_request_items from anon;
grant select,insert,update on public.cv_profiles to authenticated;
grant select,insert,update,delete on public.cv_want_lists,public.cv_want_list_items,public.cv_sourcing_requests,public.cv_sourcing_request_items to authenticated;
grant select,insert on public.cv_seller_applications to authenticated;
-- Do not expose seller approval or buyer identity to other authenticated users.
-- Seller demand discovery and anonymous aggregation require a separate reviewed RPC.
