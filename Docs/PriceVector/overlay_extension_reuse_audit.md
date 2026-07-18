# Overlay Extension Reuse Audit

Audit date: 2026-07-17

Scope: targeted inspection only. No production code, pricing behavior, or
architecture was changed.

## Source Location

The nominal active location,
`Platform/Pokemon_Live_Price_Lookup`, contains no substantive source files in
the audited working tree. The implementation available for inspection is the
historical snapshot:

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3`

All findings below refer to that archived snapshot. It is useful reference
material, but Price Vector or Marketplace Intelligence should not import code
from `Archive` at runtime.

## Executive Summary

The overlay contains a useful TCGplayer **active-listing** extractor. It can
normalize item price, shipping, delivered price, condition, finish, seller
details, listing ID, quantity, and capture time. Its best Price Vector use is
competition evidence, such as the lowest delivered active listing by condition
and finish.

The overlay does **not** contain:

- An eBay page parser.
- An eBay sold-listing parser.
- A TCGplayer recent-sales parser.
- Completed-sale dates.
- A Fair Market Value calculation based on sold evidence.
- Automated marketplace-parser tests.

The active-listing result must therefore not be treated as Fair Market Value or
as proof of a completed sale. Several components are useful with adaptation,
but none of the archived runtime modules should be copied directly into the
canonical pricing path without isolating their old browser, local-server,
database, float-math, and provider assumptions.

## Marketplace Coverage

| Capability | Finding |
| --- | --- |
| TCGplayer active listings | Present through a JSON endpoint used by `live_tcgplayer_prices.py`. |
| TCGplayer product-page HTML | Diagnostic fetch only. The saved page contained no usable price values. |
| TCGplayer recent sales | Not found. |
| TCGplayer Market Price | Available only through cached/provider values and a TCGdex fallback, not a verified recent-sales feed. |
| eBay active page parsing | Not found. |
| eBay sold parsing | Not found. |
| Price extraction | Present for TCGplayer active listings. |
| Shipping extraction | Present for TCGplayer active listings. |
| Condition extraction | Present for TCGplayer active listings. |
| Seller extraction | Present for TCGplayer active listings. |
| Listing type extraction | Raw response contains `listingType`, but the normalizer drops it. |
| Sale-date extraction | Not found. |
| Source URL | Partial: product/provider URLs are stored elsewhere, but normalized listing evidence lacks a source URL. |
| Capture timestamp | Present as `fetched_at` or `as_of`. |
| Cache and delayed loading | Present. |
| Retry/backoff | Not present. Partial failures are recorded, but requests are not retried. |

The only `ebay` references found in the current and archived price-cache modules
are provider-priority labels. They do not fetch or parse eBay data.

## Reuse Classification

### 1. TCGplayer field normalization

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/live_tcgplayer_prices.py`

**Components**

- `_money_number(value)`
- `_printing_key(value)`
- `_condition_key(value)`

**Current behavior**

- Converts provider values to non-negative numeric prices.
- Normalizes `Normal`, `Holofoil`, and `Reverse Holofoil` finish labels.
- Normalizes full condition names and abbreviations to `NM`, `LP`, `MP`, `HP`,
  and `DMG`.

**Classification**

Reusable with adaptation.

**Price Vector / Marketplace Intelligence use**

- Normalize TCGplayer competition evidence before it enters a market-evidence
  record.
- Keep condition and finish labels consistent across provider fixtures.

**Required adaptation**

- Use `Decimal` or the canonical money helper instead of `float`.
- Return canonical condition and finish values already owned by Marketplace
  Intelligence rather than preserving an overlay-only dictionary shape.
- Decide explicitly how unknown conditions and finishes are represented.

**Tests or fixtures**

No automated tests. The saved active-listing JSON contains examples for these
fields.

### 2. TCGplayer active-listing request and response reader

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/live_tcgplayer_prices.py`

**Components**

- `TCGPLAYER_LISTINGS_URL`
- `_base_payload(size)`
- `_condition_payload(condition_name, size)`
- `_post_json(url, payload, timeout)`
- `_rows_from_response(data)`
- `fetch_live_listing_rows(product_id, size)`
- `fetch_live_listing_rows_for_condition(product_id, condition_name, size)`

**Current behavior**

- Posts to
  `https://mp-search-api.tcgplayer.com/v1/product/{product_id}/listings?mpfev=5245`.
- Requests live sellers, quantity of at least one, channel zero, US shipping,
  and condition/printing/listing-type aggregations.
- Uses a 25-second timeout and hard-coded browser-style request headers.
- Reads listing rows from the first result block.

**Classification**

Reusable with adaptation.

**Price Vector / Marketplace Intelligence use**

- Potential provider input for active-listing competition analysis.
- Capture the available market floor and seller competition for a known
  TCGplayer product ID.

**Required adaptation**

- Keep provider access behind Marketplace Intelligence; Price Vector must not
  call it directly.
- Verify that use of this endpoint is supported before production dependence.
  The code uses a browser-facing endpoint and browser impersonation rather than
  a documented provider client.
- Replace hard-coded headers, URL parameters, and timeout with provider
  configuration.
- Add response-schema validation, bounded retries, backoff, and explicit
  provider error categories.
- Preserve the request URL and retrieval time in each evidence record.

**Tests or fixtures**

- Manual probe:
  `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/tools/tcgplayer_live_listings_probe.py`
- Saved response:
  `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/price_cache/web_fetch_diagnostics/tcgplayer_live_listings_42402_20260610_134933.json`
- No automated contract or parser tests.

### 3. TCGplayer listing evidence extraction

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/live_tcgplayer_prices.py`

**Component**

`_listing_candidate(row, fetched_at)`

**Current behavior**

Extracts:

- `sellerPrice` or `price`
- `shippingPrice` or `sellerShippingPrice`
- Delivered total as item price plus shipping
- Seller name, sales count, and rating
- Listing ID
- Quantity
- Condition
- Printing/finish
- Source label `tcgplayer_live`
- Fetch timestamp

The raw saved response also includes `listingType`, `verifiedSeller`,
`goldSeller`, `productId`, `sellerId`, and other fields that this function does
not preserve.

**Classification**

Reusable with adaptation.

**Price Vector / Marketplace Intelligence use**

- Create normalized active-listing competition evidence.
- Compare a proposed listing price with the delivered price a buyer sees.
- Retain seller quality and quantity as optional competition context.

**Required adaptation**

- Rename `market` because the value is one active listing's delivered price,
  not market value or Fair Market Value.
- Use `Decimal`.
- Preserve provider product ID, listing type, source URL, raw provider
  condition, and capture timestamp.
- Distinguish item price, shipping, and delivered price explicitly.
- Do not invent a zero shipping cost when shipping is unknown; preserve
  unknown separately from confirmed free shipping.
- Do not classify the row as sold evidence. There is no sold status or sale
  date.

**Tests or fixtures**

The saved product `42402` response includes a concrete row with item price,
shipping, seller, condition, finish, listing ID, listing type, and quantity.
There are no assertions covering the extractor.

### 4. Lowest delivered active listing by condition and finish

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/live_tcgplayer_prices.py`

**Components**

- `_add_best_listing(summary, row, fetched_at)`
- `summarize_live_listing_prices_uncached(product_id, size)`

**Current behavior**

- Groups listings by normalized printing/finish and condition.
- Retains the lowest delivered active listing in each group.
- De-duplicates rows by listing ID.
- Fetches a general page and condition-specific pages.
- Records per-condition request failures in `condition_fetch_errors`.
- Records a sampled-listing count and fetch timestamp.

**Classification**

Reusable with adaptation.

**Price Vector / Marketplace Intelligence use**

- Active competition floor by finish and condition.
- Evidence quality warnings when one or more condition requests fail.
- Sample-count context for competition analysis.

**Required adaptation**

- Name the result as an active-listing floor, not `market`.
- Keep the complete accepted evidence set where needed; retaining only the
  cheapest row cannot support robust FMV or distribution analysis.
- Record duplicate and rejected-row counts.
- Catch failure of the initial global request as well as condition requests.
- Add deterministic tests for missing fields, unknown conditions, duplicate
  IDs, shipping, partial failures, and empty responses.

**Tests or fixtures**

Manual probe and one saved active-listing response only.

### 5. Product-level TTL cache

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/live_tcgplayer_prices.py`

**Components**

- `TCGPLAYER_PRODUCT_PRICE_CACHE`
- `TCGPLAYER_PRODUCT_PRICE_CACHE_TTL_SECONDS`
- `summarize_live_listing_prices(product_id, size)`

**Current behavior**

- Caches product/size results in memory for ten minutes.
- Adds `product_cache_hit` to the returned dictionary.

**Classification**

Reusable with adaptation.

**Price Vector / Marketplace Intelligence use**

- Avoid repeated provider requests during a single analysis run.
- Expose cache freshness as evidence provenance.

**Required adaptation**

- Use the canonical provider cache rather than create a second cache owner.
- Add a maximum size, thread safety, explicit invalidation, and immutable or
  deep-copied values.
- Keep original capture time separate from cache-return time.

**Tests or fixtures**

No automated TTL, invalidation, or concurrency tests.

### 6. Cached/live evidence merge

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/live_tcgplayer_prices.py`

**Component**

`enrich_variants_with_live_prices(variants, size)`

**Current behavior**

- Mutates overlay variant dictionaries in place.
- Matches a requested finish to live listing buckets.
- Replaces cached condition prices with live active-listing prices.
- Retains old cached values in `sources` and `cached_*` fields.
- Records live source, sample count, timestamp, and errors.

**Classification**

Not reusable safely as production code; the provenance-preservation idea is
reusable with adaptation.

**Price Vector / Marketplace Intelligence use**

- Preserve prior evidence when fresher evidence is attached.
- Display live-versus-cached provenance and warnings.

**Why direct reuse is unsafe**

- It mutates an overlay-specific variant schema.
- It overwrites semantically different cached values with one active-listing
  floor.
- It assumes product identity and finish matching have already succeeded.
- It conflates live active listings with market prices.

**Tests or fixtures**

No automated tests.

### 7. Market link and snapshot persistence pattern

**Paths**

- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/price_cache.py`
- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/tools/market_price_schema.sql`

**Components**

- `init_price_db()`
- `upsert_price_link(...)`
- `insert_price_snapshot(...)`
- `latest_prices_for_card(putnam_card_id)`
- Tables `market_price_links` and `market_price_snapshots`

**Current behavior**

- Links a CardVector-era card ID to provider product ID and provider URL.
- Stores match confidence and last verification time.
- Stores provider, condition, market/low/high values, sample size, and
  observation time.
- Selects a latest preferred provider value for display.

**Classification**

Reusable with adaptation as a provenance model, not as a direct database
implementation.

**Price Vector / Marketplace Intelligence use**

- Inform normalized evidence fields for provider identity, URL, match
  confidence, captured time, condition, and sample size.
- Preserve time-series observations instead of overwriting prior evidence.

**Required adaptation**

- Do not introduce this archived SQLite database as a competing canonical
  Marketplace Intelligence store.
- Use canonical money types rather than SQLite `real`/Python `float`.
- Store individual evidence records and evidence type, not only aggregate
  low/market/high values.
- Separate identity-match confidence from market-evidence confidence.
- Preserve source URL on each observation.
- Remove provider priority as an implicit substitute for evidence weighting.
- Do not reuse the archived raw-card provider priority that includes
  `pricecharting`.

**Tests or fixtures**

- CSV input example:
  `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/tools/tcgplayer_price_import_template.csv`
- Runtime database:
  `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/runtime/market_prices.sqlite`
- No automated repository or migration tests.

### 8. TCGdex TCGplayer market-price fallback

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/tools/tcgdex_prices.py`

**Components**

- `normalize_tcgdex_card_id(tcgdex_card_id)`
- `fetch_json(url)`
- `select_tcgplayer_market(pricing)`
- `refresh_one(putnam_card_id, tcgdex_card_id)`
- `refresh_from_csv(csv_path)`

**Current behavior**

- Fetches a TCGdex card record.
- Selects a TCGplayer pricing variant with a configured finish priority.
- Stores market, low, and high values as a `MARKET` snapshot.
- Continues to the next CSV row after common network/data errors.

**Classification**

Reusable with adaptation as supporting reference evidence only.

**Price Vector / Marketplace Intelligence use**

- Supply a clearly labeled, reference-only TCGplayer Market Price proxy when
  primary sold evidence is unavailable.

**Required adaptation**

- Keep TCGdex as the actual provider and record that its payload reports a
  TCGplayer-derived field.
- Do not use it as TCGplayer recent-sales evidence.
- Use `Decimal`, retries, provider configuration, capture timestamps, and
  response-schema tests.

**Tests or fixtures**

No saved TCGdex response or automated tests were found.

### 9. Local price service and session cache

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/viewer_server.py`

**Components**

- `PRICE_SESSION_CACHE`
- `cached_latest_prices_for_card(putnam_card_id)`
- `send_json(handler, payload, status)`
- `ViewerHandler` route `/api/prices`

**Current behavior**

- Caches price payloads by card ID for ten minutes.
- Returns cache-hit metadata.
- Exposes prices through a local unauthenticated HTTP endpoint.
- Returns concise HTTP errors for missing IDs on several routes.

**Classification**

Not reusable directly. Cache and response-contract behavior is reusable with
adaptation.

**Price Vector / Marketplace Intelligence use**

- Inform a lightweight evidence-loading boundary and cache-status display.
- Keep provider work out of UI rendering.

**Browser/overlay assumptions to remove**

- Localhost port `8790`.
- Overlay-specific card catalog and response shape.
- Broad CORS response.
- No authentication or production service boundary.
- In-memory mutable cache without size or concurrency controls.

**Tests or fixtures**

No server-route or cache tests.

### 10. Evidence price presentation

**Paths**

- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/extension/overlay.js`
- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/extension/overlay.css`

**Components**

- `money(value)`
- `pickPrice(prices, keys)`
- `priceObject(variant, condition)`
- `priceValue(item)`
- `priceText(item)`
- `hasUsablePrices(prices)`
- `formatFinish(value)`
- `formatUpdated(value)`
- `renderCompactConditionCell(variant, condition, url)`
- `renderVariantPrices(card, prices)`
- CSS states `.ppo-live-source`, `.ppo-cache-source`,
  `.ppo-price-loading`, `.ppo-price-error`, and `.ppo-price-queued`

**Current behavior**

- Presents NM, LP, and MP prices by finish.
- Distinguishes live TCGplayer values from cached values.
- Shows observation time.
- Links displayed prices to a product page.
- Shows explicit empty, loading, and failure states.

**Classification**

Reusable with adaptation as UI behavior and information hierarchy; not reusable
directly as a desktop or canonical Price Vector component.

**Price Vector / Marketplace Intelligence use**

- Evidence rows showing condition, finish, source, price, and observation time.
- Consistent live/cached, loading, empty, and failed states.
- Price-comparison links that preserve source provenance.

**Browser/overlay assumptions to remove**

- Injected DOM and `ppo-*` CSS classes.
- Overlay-global state and local backend URL.
- Variant/card matching helpers.
- JavaScript float formatting.
- Extension-specific layout and event handlers.

The overlay displays a `variant_match_rank`; that value concerns product/card
matching and must not be reused as Price Vector market-evidence confidence.

**Tests or fixtures**

No component, DOM, accessibility, or screenshot tests.

### 11. Lazy evidence loading and bounded concurrency

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/extension/overlay.js`

**Components**

- `loadLazyPrices(card, mount)`
- `enqueueLazyPriceLoad(card, mount)`
- `processLazyPriceQueue()`
- `LAZY_PRICE_CONCURRENCY`
- `LAZY_PRICE_BATCH_DELAY_MS`

**Current behavior**

- Loads price data after search results render.
- Limits concurrent requests to four.
- Adds a short delay between completed and newly started queue work.
- Converts failures into a visible row-level error.
- Uses `finally` so queue activity is released after success or failure.

**Classification**

Reusable with adaptation as an asynchronous UI pattern.

**Price Vector / Marketplace Intelligence use**

- Keep evidence retrieval from freezing a review screen.
- Display per-row loading and failure status while preserving other results.

**Browser/overlay assumptions to remove**

- DOM mount replacement.
- Fetches the localhost `/api/prices` route.
- No cancellation, retry, stale-result guard, or application shutdown handling.

**Tests or fixtures**

No concurrency, ordering, or failure tests.

### 12. Chrome service-worker request wrapper

**Path**

`Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/extension/background.js`

**Components**

- `normalizeBackendUrl(value)`
- `getBackendUrl()`
- `fetchJson(path, params)`
- Chrome message handlers for health and search

**Current behavior**

- Reads a configurable localhost backend URL from `chrome.storage.local`.
- Adds query parameters, disables browser caching, checks HTTP status, and
  converts failures to concise extension messages.

**Classification**

Not reusable directly.

**Price Vector / Marketplace Intelligence use**

The concise health/error contract is a useful reference, but this file provides
no marketplace parser or evidence logic.

**Browser/overlay assumptions to remove**

- `chrome.runtime` and `chrome.storage`.
- Service-worker messaging.
- Local server process and port.
- Search/card-identification fields outside this audit.

**Tests or fixtures**

No service-worker tests.

### 13. TCGplayer diagnostic capture tools

**Paths**

- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/tools/tcgplayer_live_listings_probe.py`
- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/tools/tcgplayer_page_probe.py`

**Components**

- `post_json(url, payload)`
- `tcgplayer_direct_url(url)`
- `product_url_from_cache(product_id)`
- `fetch_url(url)`
- `summarize_html(html)`
- Both `main()` entry points

**Current behavior**

- Captures raw TCGplayer active-listing JSON.
- Captures product-page HTML and a JSON diagnostic summary.
- Preserves fetched URL, HTTP status, selected response headers, content size,
  marker presence, and discovered price-like strings.
- Handles HTTP, URL, and timeout failures with diagnostic output.

**Classification**

Reusable with adaptation as fixture-capture and provider-diagnostic tools.

**Price Vector / Marketplace Intelligence use**

- Produce reproducible provider-contract fixtures.
- Diagnose provider page changes without changing pricing behavior.
- Retain URL and retrieval metadata beside raw evidence.

**Required adaptation**

- Remove dependency on the overlay's `tcgtracking_cache.sqlite` and project-root
  discovery.
- Add explicit output-path configuration and redaction checks.
- Record retrieval time in the page summary itself.
- Avoid treating regex-discovered currency strings as parsed evidence.
- Add a fixture manifest and deterministic parser assertions before production
  use.

**Tests or fixtures**

- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/price_cache/web_fetch_diagnostics/tcgplayer_probe_42402_20260610_133657.html`
- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/price_cache/web_fetch_diagnostics/tcgplayer_probe_42402_20260610_133657.json`
- `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/price_cache/web_fetch_diagnostics/tcgplayer_live_listings_42402_20260610_134933.json`

The saved HTML is particularly useful as a negative fixture: it returned HTTP
200 but contained no market, low, or obvious dollar values, demonstrating that
initial product HTML cannot be assumed to contain pricing data.

## Existing Fixture And Test Coverage

### Saved marketplace artifacts

| Artifact | Coverage |
| --- | --- |
| `tcgplayer_live_listings_42402_20260610_134933.json` | One raw active-listing response with 491 total results and 10 returned rows. Includes listing type, condition, finish, item price, shipping, seller data, quantity, and listing ID. |
| `tcgplayer_probe_42402_20260610_133657.html` | One initial product-page HTML response. It contains no usable price values. |
| `tcgplayer_probe_42402_20260610_133657.json` | Diagnostic summary for the saved HTML, including URL, status, selected headers, and content markers. |
| `tcgplayer_price_import_template.csv` | One synthetic CSV row for provider link and NM/LP aggregate import. |

### Missing automated coverage

No marketplace parser test suite, JavaScript component tests, fixture-driven
contract tests, retry tests, cache tests, or eBay fixtures were found in the
snapshot. Files named `inspect_*.py` are manual inspection utilities, not
automated tests.

Before any implementation reuse, the saved TCGplayer JSON should be used to
lock down expected normalization behavior without making live provider calls.

## Components Too Tightly Coupled To Reuse Safely

The following should not be imported into Marketplace Intelligence or Price
Vector as-is:

1. `extension/overlay.js`: injected-page DOM, overlay globals, card-search
   state, and localhost fetches are inseparable from its rendering functions.
2. `extension/overlay.css`: selectors and layout are tied to the `ppo-*`
   extension DOM. The state vocabulary is useful, not the stylesheet itself.
3. `extension/background.js`: depends on Chrome service-worker and storage
   APIs.
4. `backend/viewer_server.py`: combines local HTTP transport, card catalog,
   thumbnail delivery, search, and pricing.
5. `backend/price_cache.py:latest_prices_for_card()`: combines product identity
   matching, variant ranking, old SQLite layouts, provider selection, and live
   enrichment. Its identity and recognition-adjacent matching logic is outside
   this audit.
6. `backend/live_tcgplayer_prices.py:enrich_variants_with_live_prices()`:
   mutates the overlay's variant dictionaries and conflates active listing
   floors with cached market values.
7. Historical `install_*` patch scripts and `archive_old_versions` copies:
   these record evolution, but are not authoritative implementations.

## Safe Reuse Boundary

The safest value to carry forward is:

1. The raw TCGplayer active-listing fixture.
2. The condition, finish, shipping, seller, and delivered-price normalization
   behavior.
3. The per-source timestamp, URL, sample-count, cache-status, and partial-error
   provenance ideas.
4. The bounded lazy-loading and explicit loading/empty/failure UI states.

Any future reuse should preserve these boundaries:

- Market Intelligence owns provider access and normalized evidence.
- Price Vector consumes FMV and competition context; it does not call the
  overlay or provider endpoints.
- TCGplayer active listings are competition evidence, not sold evidence.
- TCGdex or cached market values are supporting evidence only unless their
  provenance and approved role say otherwise.
- No overlay identity, OCR, image, scanner, camera, or recognition code belongs
  in the Price Vector path.

## Audit Conclusion

The archived overlay can save effort in a future Marketplace Intelligence
provider implementation, especially around TCGplayer active-listing field
mapping, delivered-price comparison, capture provenance, partial failure
reporting, and evidence display.

It cannot supply the approved primary FMV evidence by itself. There is no
eBay sold parser, no TCGplayer recent-sales parser, and no sale-date extraction.
The existing lowest-active-listing calculation should be retained only as
competition context and should never be renamed or promoted to Fair Market
Value.
