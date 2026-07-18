create table if not exists price_vector_pricing_decisions (
  decision_id text primary key,
  listing_reference text not null,
  fair_market_value text,
  fair_market_value_confidence text not null default 'none',
  recommended_listing_price text not null,
  final_listing_price text not null,
  pricing_reasoning text not null default '',
  market_evidence_reference text not null default '',
  created_at text not null
);

create index if not exists idx_price_vector_decisions_listing_created
  on price_vector_pricing_decisions (listing_reference, created_at);
