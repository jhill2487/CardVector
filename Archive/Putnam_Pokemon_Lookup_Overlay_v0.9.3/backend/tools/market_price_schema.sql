create table if not exists market_price_links (
  putnam_card_id text not null,
  provider text not null,
  provider_product_id text,
  provider_url text,
  match_confidence real default 0,
  last_verified_at text,
  primary key (putnam_card_id, provider)
);

create table if not exists market_price_snapshots (
  snapshot_id integer primary key autoincrement,
  putnam_card_id text not null,
  provider text not null,
  condition text not null, -- NM, LP, or MARKET fallback
  market_price real,
  low_price real,
  high_price real,
  sample_size integer,
  as_of text not null default (datetime('now'))
);

create index if not exists idx_market_price_snapshots_card
  on market_price_snapshots (putnam_card_id, provider, condition, as_of);
