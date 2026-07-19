# Comparable Matching

## Current Accepted Signals

- SKU or catalog identity when present
- normalized card-name tokens, with a 90 percent token threshold
- collector number, including normalized leading-zero handling
- a conservative set-name title token
- exclusion of graded, slab, lot, playset, pack, booster, box, deck, sealed,
  bundle, binder, proxy, custom, reprint, metal, jumbo, and related terms

Normal repository execution routes provider matching through the canonical
evidence diagnostics. Existing accepted/rejected behavior remains
characterized for valid, graded, wrong-name, and wrong-number cases.

## False-Match Risk

The current source evidence often contains only title and price. It does not
reliably prove:

- English versus Japanese, Korean, or Chinese language
- holo versus reverse-holo finish
- promo versus set release
- first-edition, unlimited, or shadowless variant
- marketplace condition
- graded company or grade when a title omits obvious terms
- seller quality
- completed-sale date
- duplicate sale identity

When a listing declares variant or finish but provider metadata does not prove
the same variant, Phase 7 emits `VARIANT_UNVERIFIED`. Promo identities emit
`PROMO_VARIANT`. These are advisory controls and do not silently change the
historical accepted-comparable set.

## Future Accuracy Improvements

The next approved pricing-method change should require structured language,
condition, finish, edition, and sale date in `MarketEvidence`; deduplicate by
marketplace sale identifier; then characterize condition-matched and
variant-matched fixtures before enabling automatic approval. Seller quality
should be a quality signal, not a substitute for card identity.

No such matching-math change is hidden in Phase 7.
