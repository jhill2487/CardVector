from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re

ROOT = Path.cwd()
BACKEND = ROOT / "backend"
EXT = ROOT / "extension"
VIEWER = BACKEND / "viewer_server.py"
OVERLAY = EXT / "overlay.js"
CSS = EXT / "overlay.css"
MANIFEST = EXT / "manifest.json"
ARCHIVE = ROOT / "archive_old_versions"
NOTES = ROOT / "docs" / "release_notes"

ARCHIVE.mkdir(exist_ok=True)
NOTES.mkdir(parents=True, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

viewer = VIEWER.read_text(encoding="utf-8")
overlay = OVERLAY.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
manifest_text = MANIFEST.read_text(encoding="utf-8")

(ARCHIVE / f"viewer_server_before_v0_5_0_{stamp}.py").write_text(viewer, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_5_0_{stamp}.js").write_text(overlay, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_5_0_{stamp}.css").write_text(css, encoding="utf-8")
(ARCHIVE / f"manifest_before_v0_5_0_{stamp}.json").write_text(manifest_text, encoding="utf-8")


def replace_function(source: str, function_name: str, new_function: str) -> str:
    marker = f"  function {function_name}("
    start = source.find(marker)
    if start == -1:
        marker = f"  async function {function_name}("
        start = source.find(marker)
    if start == -1:
        raise SystemExit(f"ERROR: Could not find function {function_name}().")

    brace_start = source.find("{", start)
    depth = 0
    end = None
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise SystemExit(f"ERROR: Could not parse function {function_name}().")

    return source[:start] + new_function.rstrip() + source[end:]


# ----------------------------
# Backend: /api/search pagination
# ----------------------------
search_start = viewer.find('        if parsed.path == "/api/search":')
if search_start == -1:
    raise SystemExit('ERROR: Could not find /api/search block in viewer_server.py.')

next_markers = [
    '        if parsed.path == "/api/prices":',
    '        if parsed.path == "/api/thumb-card":',
]
search_end_candidates = [viewer.find(m, search_start + 1) for m in next_markers if viewer.find(m, search_start + 1) != -1]
if not search_end_candidates:
    raise SystemExit("ERROR: Could not find end of /api/search block.")
search_end = min(search_end_candidates)

new_search_block = '''        if parsed.path == "/api/search":
            query = params.get("q", [""])[0].strip()
            set_query = params.get("set", [""])[0].strip() or None
            number_query = params.get("number", [""])[0].strip() or None

            try:
                limit = int(params.get("limit", ["20"])[0] or 20)
            except ValueError:
                limit = 20

            try:
                offset = int(params.get("offset", ["0"])[0] or 0)
            except ValueError:
                offset = 0

            try:
                price_limit = int(params.get("price_limit", ["0"])[0] or 0)
            except ValueError:
                price_limit = 0

            limit = max(1, min(limit, 50))
            offset = max(0, offset)

            # Request one extra result so the UI knows whether LOAD MORE should appear.
            search_limit = offset + limit + 1

            all_results = search_cards(
                name=query or None,
                number=number_query,
                set_slug_or_name=set_query,
                limit=search_limit,
            )

            has_more = len(all_results) > offset + limit
            results = all_results[offset:offset + limit]

            for index, card in enumerate(results):
                card["thumbnail_url"] = f"/api/thumb-card?id={card['putnam_card_id']}"
                card["tcgplayer_search_url"] = tcgplayer_search_url(card)
                if index < price_limit:
                    card["prices"] = cached_latest_prices_for_card(card["putnam_card_id"]) if "cached_latest_prices_for_card" in globals() else latest_prices_for_card(card["putnam_card_id"])
                else:
                    card["prices"] = None

            send_json(self, {
                "ok": True,
                "results": results,
                "limit": limit,
                "offset": offset,
                "next_offset": offset + len(results),
                "has_more": has_more,
            })
            return

'''

viewer = viewer[:search_start] + new_search_block + viewer[search_end:]


# ----------------------------
# Extension: add search cache globals
# ----------------------------
if "SEARCH_PAGE_LIMIT" not in overlay:
    overlay = overlay.replace(
        '  let backendUrl = "http://127.0.0.1:8790";',
        '''  let backendUrl = "http://127.0.0.1:8790";
  const SEARCH_PAGE_LIMIT = 20;
  const SEARCH_CACHE_TTL_MS = 5 * 60 * 1000;
  const searchResultCache = new Map();
  let currentSearchState = null;
  let loadMoreButton = null;'''
    )

# Keep existing lazy constants if present. If old LAZY_PRICE_LIMIT remains, leave it alone.

# ----------------------------
# Extension: helper direct search API
# ----------------------------
if "async function fetchSearchPage" not in overlay:
    insert_marker = "  async function loadLazyPrices(card, mount) {"
    helper = '''  function normalizeSearchCacheKey(query, setQuery, numberQuery, offset) {
    return JSON.stringify({
      q: String(query || "").trim().toLowerCase(),
      set: String(setQuery || "").trim().toLowerCase(),
      number: String(numberQuery || "").trim().toLowerCase(),
      offset: Number(offset || 0),
      limit: SEARCH_PAGE_LIMIT
    });
  }

  async function fetchSearchPage(query, setQuery, numberQuery, offset) {
    const cacheKey = normalizeSearchCacheKey(query, setQuery, numberQuery, offset);
    const cached = searchResultCache.get(cacheKey);
    const now = Date.now();

    if (cached && now - cached.time < SEARCH_CACHE_TTL_MS) {
      return { ...cached.payload, search_cache_hit: true };
    }

    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (setQuery) params.set("set", setQuery);
    if (numberQuery) params.set("number", numberQuery);
    params.set("limit", String(SEARCH_PAGE_LIMIT));
    params.set("offset", String(offset || 0));
    params.set("price_limit", "0");

    const response = await fetch(`${backendUrl}/api/search?${params.toString()}`, { cache: "no-store" });
    const payload = await response.json();

    if (!payload?.ok) {
      throw new Error(payload?.error || "Search failed");
    }

    searchResultCache.set(cacheKey, { time: now, payload });
    return payload;
  }

'''
    if insert_marker not in overlay:
        raise SystemExit("ERROR: Could not find insertion point before loadLazyPrices().")
    overlay = overlay.replace(insert_marker, helper + insert_marker)


# ----------------------------
# Extension: renderResults with append + load more
# ----------------------------
new_render_results = '''  function renderResults(results, options = {}) {
    const append = Boolean(options.append);
    const payload = options.payload || {};
    const startingIndex = Number(options.startingIndex || 0);

    if (!append) {
      lazyPriceQueue = [];
      activeLazyPriceLoads = 0;
      resultsEl.replaceChildren();
    }

    if (!results.length && !append) {
      statusEl.textContent = "No matches. Try name + card number, or set + number.";
      return;
    }

    const totalShown = append
      ? resultsEl.querySelectorAll(".ppo-result").length + results.length
      : results.length;

    statusEl.textContent = `${totalShown} match${totalShown === 1 ? "" : "es"} shown${payload.search_cache_hit ? " • cached" : ""}`;

    for (const card of results) {
      const row = el("div", { className: "ppo-result" });
      const prices = card.prices || {};

      const media = el("div", { className: "ppo-media" });
      const imageUrl = absoluteUrl(prices?.variants?.[0]?.image_url || card.thumbnail_url || card.image_url || card.small_image_url);
      if (imageUrl) {
        const thumb = el("img", {
          className: "ppo-thumb",
          attrs: { src: imageUrl, alt: card.card_name || "Pokemon card image", loading: "lazy" }
        });
        media.append(thumb);
      }

      const details = el("div", { className: "ppo-result-details" });

      function displaySetName(card) {
        const raw = String(card.set_name || card.set || "UNKNOWN SET").trim();
        if (raw.toLowerCase() === "151") return "SV: SCARLET & VIOLET 151";
        return raw.toUpperCase();
      }

      const setLine = `${displaySetName(card)} ${card.printed_number || card.card_number || card.number || ""}`.trim().toUpperCase();
      details.append(
        el("strong", { text: String(card.card_name || card.name || "UNKNOWN CARD").toUpperCase() }),
        el("span", { className: "ppo-card-setline", text: setLine }),
        el("span", { className: "ppo-card-rarity", text: card.rarity ? `RARITY: ${String(card.rarity).toUpperCase()}` : "" }),
        el("span", { text: card.confidence ? `DATABASE MATCH: ${Math.round(Number(card.confidence) * 100)}%` : "" })
      );

      const priceMount = el("div", { className: "ppo-price-mount" });
      const resultIndex = startingIndex + results.indexOf(card);
      const shouldLoadInitial = resultIndex < INITIAL_LAZY_PRICE_LIMIT;
      const shouldLoadBackground = resultIndex < BACKGROUND_LAZY_PRICE_LIMIT;

      if (prices && Object.keys(prices).length) {
        priceMount.append(renderVariantPrices(card, prices));
      } else if (shouldLoadInitial && card.putnam_card_id) {
        priceMount.append(el("div", {
          className: "ppo-price-loading",
          text: "LOADING LIVE PRICE..."
        }));
        enqueueLazyPriceLoad(card, priceMount);
      } else if (shouldLoadBackground && card.putnam_card_id) {
        priceMount.append(el("div", {
          className: "ppo-price-loading ppo-price-queued",
          text: "QUEUED LIVE PRICE..."
        }));
        enqueueLazyPriceLoad(card, priceMount);
      } else {
        priceMount.append(renderVariantPrices(card, prices));
      }

      details.append(priceMount);
      row.append(media, details);
      resultsEl.append(row);
    }

    renderLoadMoreButton(payload);
  }'''

overlay = replace_function(overlay, "renderResults", new_render_results)


# ----------------------------
# Extension: load more button
# ----------------------------
if "function renderLoadMoreButton" not in overlay:
    marker = "  async function loadSettings() {"
    load_more_code = '''  function renderLoadMoreButton(payload) {
    if (loadMoreButton) {
      loadMoreButton.remove();
      loadMoreButton = null;
    }

    if (!payload?.has_more || !currentSearchState) return;

    loadMoreButton = el("button", {
      className: "ppo-load-more",
      type: "button",
      text: "LOAD MORE RESULTS"
    });

    loadMoreButton.addEventListener("click", () => {
      loadMoreResults().catch((error) => {
        statusEl.textContent = error.message || "Load more failed.";
      });
    });

    resultsEl.append(loadMoreButton);
  }

  async function loadMoreResults() {
    if (!currentSearchState) return;

    loadMoreButton.disabled = true;
    loadMoreButton.textContent = "LOADING MORE...";

    const payload = await fetchSearchPage(
      currentSearchState.query,
      currentSearchState.setQuery,
      currentSearchState.numberQuery,
      currentSearchState.nextOffset
    );

    const startingIndex = currentSearchState.nextOffset;
    currentSearchState.nextOffset = payload.next_offset || (currentSearchState.nextOffset + (payload.results || []).length);
    currentSearchState.hasMore = Boolean(payload.has_more);

    renderResults(payload.results || [], {
      append: true,
      payload,
      startingIndex
    });
  }

'''
    if marker not in overlay:
        raise SystemExit("ERROR: Could not find insertion point before loadSettings().")
    overlay = overlay.replace(marker, load_more_code + marker)


# ----------------------------
# Extension: replace search() with direct cached paginated search
# ----------------------------
new_search = '''  async function search() {
    const query = queryInput.value.trim();
    const setQuery = setInput.value.trim();
    const numberQuery = numberInput.value.trim();

    if (!query && !setQuery && !numberQuery) {
      statusEl.textContent = "Enter a card name, set, or number.";
      resultsEl.replaceChildren();
      return;
    }

    await loadSettings();

    currentSearchState = {
      query,
      setQuery,
      numberQuery,
      nextOffset: 0,
      hasMore: false
    };

    statusEl.textContent = "SEARCHING LOCAL POKEMON DATABASE...";
    const payload = await fetchSearchPage(query, setQuery, numberQuery, 0);

    currentSearchState.nextOffset = payload.next_offset || (payload.results || []).length;
    currentSearchState.hasMore = Boolean(payload.has_more);

    renderResults(payload.results || [], {
      append: false,
      payload,
      startingIndex: 0
    });
  }'''

overlay = replace_function(overlay, "search", new_search)


# ----------------------------
# CSS
# ----------------------------
if "Patch v0.5.0 - Smart Cache and Pagination" not in css:
    css += r'''

/* Patch v0.5.0 - Smart Cache and Pagination */
.ppo-load-more {
  width: 100%;
  margin: 10px 0 4px 0;
  padding: 10px 12px;
  border: 1px solid #165df5;
  border-radius: 8px;
  background: #165df5;
  color: #ffffff;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
}

.ppo-load-more:hover {
  background: #004ce8;
}

.ppo-load-more:disabled {
  opacity: 0.7;
  cursor: wait;
}

.ppo-price-queued {
  color: #374151;
  background: #f9fafb;
}
'''


# ----------------------------
# Manifest + notes
# ----------------------------
manifest = json.loads(manifest_text)
manifest["version"] = "0.5.0"

VIEWER.write_text(viewer, encoding="utf-8")
OVERLAY.write_text(overlay, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

(NOTES / "v0.5.0.md").write_text("""# Putnam Pokemon Lookup Overlay v0.5.0

## Added
- Smart Search Result Cache.
- Paginated search results.
- LOAD MORE RESULTS button.
- Backend /api/search limit and offset support.

## Improved
- Broad searches no longer stop at the first page of results.
- Repeat searches are cached client-side for faster response.
- Progressive price/image loading continues working with appended results.

## Version
- Chrome extension manifest updated to v0.5.0.
""", encoding="utf-8")

print("v0.5.0 installed.")
print("Added Smart Search Cache + Pagination + LOAD MORE RESULTS.")
print("Extension manifest updated to v0.5.0.")
print("Backups saved to:", ARCHIVE)