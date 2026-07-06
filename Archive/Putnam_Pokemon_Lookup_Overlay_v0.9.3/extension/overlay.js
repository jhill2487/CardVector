(function () {
  const existing = document.getElementById("putnam-pokemon-overlay");
  if (existing) return;

  let backendUrl = "http://127.0.0.1:8790";
  const SEARCH_PAGE_LIMIT = 20;
  const SEARCH_CACHE_TTL_MS = 5 * 60 * 1000;
  const searchResultCache = new Map();
  const imageBlobUrlCache = new Map();
  let currentSearchState = null;
  const SUGGEST_LIMIT = 10;
  let suggestTimer = null;
  let activeSuggestionIndex = -1;
  let currentSuggestions = [];
  let selectedSuggestion = null;

  // v0.6.4A history/favorites
  const HISTORY_KEY = "putnamLookupSearchHistory";
  const FAVORITES_KEY = "putnamLookupFavorites";
  const HISTORY_LIMIT = 20;
  let searchHistory = [];
  let favorites = {};
  let loadMoreButton = null;
  const INITIAL_LAZY_PRICE_LIMIT = 6;
  const BACKGROUND_LAZY_PRICE_LIMIT = 9999;
  const LAZY_PRICE_CONCURRENCY = 4;
  const LAZY_PRICE_BATCH_DELAY_MS = 60;

  let lazyPriceQueue = [];
  let activeLazyPriceLoads = 0;
  const lazyPriceCardIdsQueued = new Set();

  function sendMessage(message) {
    return new Promise((resolve) => chrome.runtime.sendMessage(message, resolve));
  }

  function el(tag, options = {}, children = []) {
    const node = document.createElement(tag);
    if (options.className) node.className = options.className;
    if (options.id) node.id = options.id;
    if (options.text !== undefined) node.textContent = options.text;
    if (options.type) node.type = options.type;
    if (options.placeholder) node.placeholder = options.placeholder;
    if (options.title) node.title = options.title;
    for (const [name, value] of Object.entries(options.attrs || {})) {
      node.setAttribute(name, value);
    }
    for (const child of children) node.append(child);
    return node;
  }

  function money(value) {
    const number = Number(value);
    if (!Number.isFinite(number) || number <= 0) return "";
    return `$${number.toFixed(number >= 100 ? 0 : 2)}`;
  }

  function pickPrice(prices, keys) {
    for (const key of keys) {
      const value = prices?.[key]?.market ?? prices?.[key]?.market_price ?? prices?.[key];
      const formatted = money(value);
      if (formatted) return formatted;
    }
    return "";
  }

  function absoluteUrl(path) {
    if (!path) return "";
    if (/^https?:\/\//i.test(path)) return path;
    return `${backendUrl}${path.startsWith("/") ? "" : "/"}${path}`;
  }

  function isLocalBackendUrl(url) {
    return /^http:\/\/(127\.0\.0\.1|localhost):8790\//i.test(String(url || ""));
  }

  async function safeImageUrl(url) {
    const full = absoluteUrl(url);
    if (!full) return "";

    if (!isLocalBackendUrl(full)) return full;

    const cached = imageBlobUrlCache.get(full);
    if (cached) return cached;

    const response = await fetch(full, { cache: "force-cache" });
    if (!response.ok) throw new Error("Image fetch failed");
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    imageBlobUrlCache.set(full, blobUrl);
    return blobUrl;
  }

  function setImageSourceSafe(img, url) {
    const full = absoluteUrl(url);
    if (!img || !full) return;

    safeImageUrl(full)
      .then((safeUrl) => {
        if (safeUrl) img.src = safeUrl;
      })
      .catch(() => {
        img.src = full;
      });
  }

  function createNoImagePlaceholder(label = "IMAGE MISSING") {
    return el("div", {
      className: "ppo-no-image",
      text: label
    });
  }

  function attachImageFallback(img, media) {
    img.addEventListener("error", () => {
      img.remove();
      if (!media.querySelector(".ppo-no-image")) {
        media.prepend(createNoImagePlaceholder());
      }
    }, { once: true });
  }

  function conditionCell(conditions, key) {
    const item = conditions?.[key];
    const value = money(item?.market);
    return value || "—";
  }

  function variantLabel(variant) {
    const pieces = [];
    if (variant.set_name) pieces.push(variant.set_name);
    if (variant.product_name) pieces.push(variant.product_name);
    if (variant.card_number) pieces.push(variant.card_number);
    if (variant.finish && variant.finish !== "normal") pieces.push(variant.finish);
    return pieces.join(" • ") || "Variant";
  }

  function priceObject(variant, condition) {
    return variant?.conditions?.[condition] || null;
  }

  function priceValue(item) {
    return item?.market ?? item?.market_price ?? item?.low ?? item?.price ?? null;
  }

  function priceText(item) {
    const value = priceValue(item);
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value);
    return `$${number.toFixed(2)}`;
  }

  function hasUsablePrices(prices) {
    if (!prices || typeof prices !== "object") return false;

    const variants = Array.isArray(prices.variants) ? prices.variants : [];
    if (variants.some((variant) => {
      const conditions = variant?.conditions || {};
      return ["NM", "LP", "MP"].some((condition) => priceText(conditions[condition]) !== "—");
    })) {
      return true;
    }

    return ["NM", "LP", "MP"].some((condition) => priceText(prices[condition]) !== "—");
  }

  function formatFinish(value) {
    const raw = String(value || "Normal").trim();
    if (!raw || raw.toLowerCase() === "normal") return "Normal";
    return raw
      .replace(/reverse holofoil/i, "REVERSE HOLO")
      .replace(/holofoil/i, "HOLO")
      .toUpperCase();
  }

  function formatUpdated(value) {
    if (!value) return "";
    const date = new Date(String(value).replace(" ", "T"));
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function firstRankedVariant(prices) {
    const variants = Array.isArray(prices?.variants) ? [...prices.variants] : [];
    variants.sort((a, b) => Number(b?.variant_match_rank || 0) - Number(a?.variant_match_rank || 0));
    return variants[0] || null;
  }

  function productLink(variant, card) {
    return variant?.tcgplayer_url || variant?.product_url || card?.tcgplayer_search_url || card?.tcgplayer_url || "";
  }

  function getBestPreviewImageUrl(card, prices) {
    return absoluteUrl(
      prices?.variants?.[0]?.image_url ||
      card?.image_large_url ||
      card?.large_image_url ||
      card?.image_small_url ||
      card?.small_image_url ||
      card?.image_url ||
      card?.thumbnail_url
    );
  }

  function openImagePreview(previewUrl, altText = "Pokemon card preview") {
    if (!previewUrl) return;

    let preview = document.getElementById("ppo-image-preview");
    if (!preview) {
      preview = el("div", { id: "ppo-image-preview", className: "ppo-image-preview" });
      document.documentElement.appendChild(preview);
    }

    const img = el("img", {
      attrs: {
        alt: altText
      }
    });
    setImageSourceSafe(img, previewUrl);

    preview.replaceChildren(img);
    preview.classList.add("ppo-image-preview-open");
  }

  function closeImagePreview() {
    const preview = document.getElementById("ppo-image-preview");
    if (preview) preview.classList.remove("ppo-image-preview-open");
  }

  function attachImageHoverPreview(img, card, prices) {
    if (!img) return;
    const previewUrl = getBestPreviewImageUrl(card, prices);
    if (!previewUrl) return;

    img.addEventListener("mouseenter", () => {
      openImagePreview(previewUrl, card?.card_name || "Pokemon card preview");
    });

    img.addEventListener("mouseleave", closeImagePreview);
  }

  function attachVariantRowHoverPreview(row, variant) {
    if (!row || !variant?.image_url) return;

    row.classList.add("ppo-variant-preview-row");
    row.addEventListener("mouseenter", () => {
      openImagePreview(
        absoluteUrl(variant.image_url),
        variant.product_name || "Pokemon card variant preview"
      );
    });
    row.addEventListener("mouseleave", closeImagePreview);
  }

  function compactVariantLabel(variant) {
    const name = String(variant?.product_name || "").toLowerCase();
    const finish = String(variant?.finish || "").toLowerCase();

    const variantPatterns = [
      ["energy symbol pattern", "ENERGY SYMBOL"],
      ["friend ball", "FRIEND BALL"],
      ["love ball", "LOVE BALL"],
      ["poke ball", "POKE BALL"],
      ["poké ball", "POKE BALL"],
      ["master ball", "MASTER BALL"],
      ["ultra ball", "ULTRA BALL"],
      ["great ball", "GREAT BALL"],
      ["team rocket", "TEAM ROCKET"],
      ["cosmos holo", "COSMOS"],
      ["cosmos", "COSMOS"],
      ["prerelease", "PRERELEASE"],
      ["pre-release", "PRERELEASE"],
      ["staff", "STAFF"],
      ["league", "LEAGUE"],
      ["stamped", "STAMPED"],
      ["stamp", "STAMPED"],
      ["promo", "PROMO"],
      ["1st edition", "1ST EDITION"],
      ["first edition", "1ST EDITION"],
      ["shadowless", "SHADOWLESS"],
      ["unlimited", "UNLIMITED"]
    ];

    for (const [needle, label] of variantPatterns) {
      if (name.includes(needle)) return label;
    }

    if (!finish || finish === "normal") return "NORMAL";
    if (finish.includes("reverse")) return "REVERSE";
    if (finish.includes("holo")) return "HOLO";
    if (finish.includes("cosmos")) return "COSMOS";

    return formatFinish(finish);
  }

  function samePrintedNumber(card, variant) {
    const clean = (value) => String(value || "").toLowerCase().replace(/[^a-z0-9/]/g, "").replace(/^0+/, "");
    const cardPrinted = clean(card?.printed_number || card?.card_number);
    const variantPrinted = clean(variant?.card_number || variant?.clean_number);

    if (!cardPrinted || !variantPrinted) return true;
    if (cardPrinted === variantPrinted) return true;

    const cardHead = cardPrinted.split("/")[0].replace(/^0+/, "");
    const variantHead = variantPrinted.split("/")[0].replace(/^0+/, "");
    return Boolean(cardHead && variantHead && cardHead === variantHead && !variantPrinted.includes("/"));
  }

  function renderCompactConditionCell(variant, condition, url) {
    const obj = priceObject(variant, condition);
    const text = `${condition} ${priceText(obj)}`;
    const cell = el("span", {
      className: `ppo-compact-price-cell ${obj?.source === "tcgplayer_live" ? "ppo-live-source" : "ppo-cache-source"}`
    });

    if (url && priceText(obj) !== "—") {
      cell.append(el("a", { text, attrs: { href: url, target: "_blank", rel: "noopener noreferrer" } }));
    } else {
      cell.textContent = text;
    }

    return cell;
  }

  function renderVariantPrices(card, prices) {
    const variants = Array.isArray(prices?.variants) ? [...prices.variants] : [];

    if (!variants.length) {
      const nm = pickPrice(prices, ["NM", "near_mint", "Near Mint"]);
      const lp = pickPrice(prices, ["LP", "lightly_played", "Lightly Played"]);
      const mp = pickPrice(prices, ["MP", "moderately_played", "Moderately Played"]);
      const market = pickPrice(prices, ["MARKET", "market", "raw"]);
      const priceTextValue = nm || lp || mp
        ? `${nm ? `NM ${nm}` : ""}${nm && lp ? " " : ""}${lp ? `LP ${lp}` : ""}${(nm || lp) && mp ? " " : ""}${mp ? `MP ${mp}` : ""}`.trim()
        : market
          ? `Market ${market}`
          : "No live price";

      return el("div", {
        className: `ppo-price-badge ${nm || lp || mp || market ? "" : "ppo-muted-price"}`,
        text: priceTextValue
      });
    }

    variants.sort((a, b) => Number(b?.variant_match_rank || 0) - Number(a?.variant_match_rank || 0));

    const wrap = el("div", { className: "ppo-live-price-card ppo-compact-price-card" });
    wrap.append(el("div", { className: "ppo-compact-price-title", text: "PRICE" }));

    const seenLabels = new Set();
    const rows = [];

    for (const variant of variants) {
      if (!samePrintedNumber(card, variant)) continue;

      const label = compactVariantLabel(variant);
      if (seenLabels.has(label)) continue;

      const nm = priceObject(variant, "NM");
      const lp = priceObject(variant, "LP");
      const mp = priceObject(variant, "MP");

      if (priceText(nm) === "—" && priceText(lp) === "—" && priceText(mp) === "—") continue;

      seenLabels.add(label);
      rows.push(variant);

      if (rows.length >= 5) break;
    }

    if (!rows.length && variants[0]) {
      const fallback = el("div", { className: "ppo-compact-price-empty", text: "No NM / LP / MP price" });
      wrap.append(fallback);

      const firstFallback = variants[0];
      const fallbackUpdated = firstFallback?.live_fetched_at || priceObject(firstFallback, "NM")?.fetched_at || "";
      const fallbackLine = firstFallback?.live_price_source === "tcgplayer_live"
        ? `LIVE TCGPLAYER • UPDATED ${formatUpdated(fallbackUpdated) || fallbackUpdated || "NOW"}`
        : `NO USABLE CONDITION PRICE${fallbackUpdated ? ` • UPDATED ${formatUpdated(fallbackUpdated)}` : ""}`;
      wrap.append(el("div", { className: "ppo-live-meta", text: fallbackLine }));

      return wrap;
    }

    for (const variant of rows) {
      const url = productLink(variant, card);
      const row = el("div", { className: "ppo-compact-price-row" });
      attachVariantRowHoverPreview(row, variant);
      row.append(el("span", { className: "ppo-compact-variant-label", text: compactVariantLabel(variant) }));
      row.append(renderCompactConditionCell(variant, "NM", url));
      row.append(el("span", { className: "ppo-compact-separator", text: "|" }));
      row.append(renderCompactConditionCell(variant, "LP", url));
      row.append(el("span", { className: "ppo-compact-separator", text: "|" }));
      row.append(renderCompactConditionCell(variant, "MP", url));
      wrap.append(row);
    }

    const first = rows[0] || variants[0];
    const liveUpdated = first?.live_fetched_at || priceObject(first, "NM")?.fetched_at || priceObject(first, "LP")?.fetched_at || "";
    const liveLine = first?.live_price_source === "tcgplayer_live"
      ? `LIVE TCGPLAYER • UPDATED ${formatUpdated(liveUpdated) || liveUpdated || "NOW"}`
      : `CACHED PRICE${liveUpdated ? ` • UPDATED ${formatUpdated(liveUpdated)}` : ""}`;
    wrap.append(el("div", { className: "ppo-live-meta", text: liveLine }));

    return wrap;
  }

  const root = el("div", { id: "putnam-pokemon-overlay" });
  const title = el("strong", { text: "Putnam Price Lookup" });
  const toggleButton = el("button", { id: "ppo-toggle", type: "button", title: "Collapse", text: "-" });
  const closeButton = el("button", { id: "ppo-close", type: "button", title: "Close", text: "x" });
  const header = el("div", { className: "ppo-header" }, [title, el("div", { className: "ppo-actions" }, [toggleButton, closeButton])]);

  const queryInput = el("input", {
    id: "ppo-query",
    type: "search",
    placeholder: "Search card, set, or number..."
  });
  const suggestionBox = el("div", { id: "ppo-suggestions", className: "ppo-suggestions" });
  const quickBar = el("div", { className: "ppo-quickbar" });
  const historyButton = el("button", { type: "button", className: "ppo-mini-button", text: "RECENT" });
  const favoritesButton = el("button", { type: "button", className: "ppo-mini-button", text: "FAVORITES" });
  const quickList = el("div", { className: "ppo-quicklist" });
  quickBar.append(historyButton, favoritesButton, quickList);
  const submitButton = el("button", { type: "submit", text: "Search" });
  const form = el("form", { id: "ppo-search-form" }, [
    el("div", { className: "ppo-unified-search-wrap" }, [queryInput, suggestionBox]),
    submitButton
  ]);
  const statusEl = el("div", { id: "ppo-status", text: "Checking local lookup server..." });
  const resultsEl = el("div", { id: "ppo-results" });
  const body = el("div", { className: "ppo-body" }, [form, quickBar, statusEl, resultsEl]);

  root.append(header, body);
  document.documentElement.appendChild(root);

  closeButton.addEventListener("click", () => root.remove());
  toggleButton.addEventListener("click", () => {
    const collapsed = root.classList.toggle("ppo-collapsed");
    toggleButton.textContent = collapsed ? "+" : "-";
    body.hidden = collapsed;
  });

  function normalizeSearchCacheKey(query, setQuery, numberQuery, offset) {
    return JSON.stringify({
      q: String(query || "").trim().toLowerCase(),
      set: String(setQuery || "").trim().toLowerCase(),
      number: String(numberQuery || "").trim().toLowerCase(),
      offset: Number(offset || 0),
      limit: SEARCH_PAGE_LIMIT
    });
  }

  async function fetchExactCard(putnamCardId) {
    await loadSettings();

    const params = new URLSearchParams();
    params.set("id", putnamCardId);

    const response = await fetch(`${backendUrl}/api/card?${params.toString()}`, { cache: "no-store" });
    const payload = await response.json();

    if (!payload?.ok) {
      throw new Error(payload?.error || "Card lookup failed");
    }

    return payload;
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

  function bestVariantImageUrl(prices) {
    const variants = Array.isArray(prices?.variants) ? prices.variants : [];
    const variant = variants.find((item) => item?.image_url);
    return absoluteUrl(variant?.image_url || "");
  }

  function hydrateResultThumbnail(card, mount) {
    const imageUrl = bestVariantImageUrl(card?.prices || {});
    if (!imageUrl || !mount) return;

    const resultRow = mount.closest(".ppo-result");
    const media = resultRow?.querySelector(".ppo-media");
    if (!media) return;

    let img = media.querySelector(".ppo-thumb");
    if (!img) {
      img = el("img", {
        className: "ppo-thumb",
        attrs: { alt: card.card_name || "Pokemon card image", loading: "eager" }
      });
      media.prepend(img);
    }

    media.querySelectorAll(".ppo-no-image").forEach((node) => node.remove());

    setImageSourceSafe(img, imageUrl);
    attachImageFallback(img, media);
    attachImageHoverPreview(img, card, card.prices || {});
  }

  async function loadLazyPrices(card, mount) {
    if (!card?.putnam_card_id) return;

    mount.replaceChildren(el("div", {
      className: "ppo-price-loading",
      text: "LOADING LIVE PRICE..."
    }));

    const url = `${backendUrl}/api/prices?id=${encodeURIComponent(card.putnam_card_id)}`;
    const response = await fetch(url, { cache: "no-store" });
    const payload = await response.json();

    if (!payload?.ok) {
      throw new Error(payload?.error || "Price lookup failed");
    }

    card.prices = payload.prices || null;

    hydrateResultThumbnail(card, mount);

    mount.replaceChildren(renderVariantPrices(card, card.prices || {}));

    hydrateResultThumbnail(card, mount);
  }

  function enqueueLazyPriceLoad(card, mount) {
    if (!card?.putnam_card_id || !mount) return;

    // v0.6.9: do not skip duplicate card IDs.
    // Duplicate skipping caused some rendered rows to never receive prices.
    lazyPriceQueue.push({ card, mount, key: String(card.putnam_card_id) });
    processLazyPriceQueue();
  }

  function processLazyPriceQueue() {
    while (activeLazyPriceLoads < LAZY_PRICE_CONCURRENCY && lazyPriceQueue.length) {
      const task = lazyPriceQueue.shift();
      activeLazyPriceLoads += 1;

      loadLazyPrices(task.card, task.mount)
        .catch((error) => {
          task.mount.replaceChildren(el("div", {
            className: "ppo-price-loading ppo-price-error",
            text: error.message || "PRICE LOOKUP FAILED"
          }));
        })
        .finally(() => {
          activeLazyPriceLoads -= 1;
          setTimeout(processLazyPriceQueue, LAZY_PRICE_BATCH_DELAY_MS);
        });
    }
  }

  function storageGet(keys) {
    return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
  }

  function storageSet(values) {
    return new Promise((resolve) => chrome.storage.local.set(values, resolve));
  }

  async function loadUserLists() {
    const data = await storageGet([HISTORY_KEY, FAVORITES_KEY]);
    searchHistory = Array.isArray(data[HISTORY_KEY]) ? data[HISTORY_KEY] : [];
    favorites = data[FAVORITES_KEY] && typeof data[FAVORITES_KEY] === "object" ? data[FAVORITES_KEY] : {};
  }

  async function saveSearchHistory(query) {
    const clean = String(query || "").trim();
    if (!clean) return;
    searchHistory = [clean, ...searchHistory.filter((q) => q.toLowerCase() !== clean.toLowerCase())].slice(0, HISTORY_LIMIT);
    await storageSet({ [HISTORY_KEY]: searchHistory });
  }

  async function toggleFavorite(card) {
    if (!card?.putnam_card_id) return;
    if (favorites[card.putnam_card_id]) {
      delete favorites[card.putnam_card_id];
    } else {
      favorites[card.putnam_card_id] = {
        putnam_card_id: card.putnam_card_id,
        card_name: card.card_name || card.name || "Unknown Card",
        set_name: card.set_name || card.set || "",
        printed_number: card.printed_number || card.card_number || ""
      };
    }
    await storageSet({ [FAVORITES_KEY]: favorites });
  }

  function renderQuickList(type) {
    quickList.replaceChildren();

    if (type === "history") {
      if (!searchHistory.length) {
        quickList.append(el("div", { className: "ppo-quick-empty", text: "No recent searches yet." }));
      } else {
        for (const q of searchHistory.slice(0, HISTORY_LIMIT)) {
          const btn = el("button", { type: "button", className: "ppo-quick-item", text: q });
          btn.addEventListener("click", () => {
            queryInput.value = q;
            quickList.replaceChildren();
            search().catch((error) => statusEl.textContent = error.message || "Search failed.");
          });
          quickList.append(btn);
        }
      }
    }

    if (type === "favorites") {
      const favs = Object.values(favorites || {});
      if (!favs.length) {
        quickList.append(el("div", { className: "ppo-quick-empty", text: "No favorites yet." }));
      } else {
        for (const card of favs) {
          const label = `${card.card_name} • ${card.set_name}${card.printed_number ? " • " + card.printed_number : ""}`;
          const btn = el("button", { type: "button", className: "ppo-quick-item", text: label.toUpperCase() });
          btn.addEventListener("click", () => {
            selectedSuggestion = card;
            queryInput.value = label;
            quickList.replaceChildren();
            search().catch((error) => statusEl.textContent = error.message || "Search failed.");
          });
          quickList.append(btn);
        }
      }
    }

    quickList.classList.toggle("ppo-quicklist-open", Boolean(quickList.childNodes.length));
  }

  function renderResults(results, options = {}) {
    const append = Boolean(options.append);
    const payload = options.payload || {};
    const startingIndex = Number(options.startingIndex || 0);

    if (!append) {
      lazyPriceQueue = [];
      lazyPriceCardIdsQueued.clear();
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
      const imageUrl = absoluteUrl(
        prices?.variants?.[0]?.image_url ||
        card.image_small_url ||
        card.small_image_url ||
        card.image_url ||
        card.image_large_url ||
        card.large_image_url ||
        card.thumbnail_url
      );
      if (imageUrl) {
        const thumb = el("img", {
          className: "ppo-thumb",
          attrs: { alt: card.card_name || "Pokemon card image", loading: "eager" }
        });
        setImageSourceSafe(thumb, imageUrl);
        attachImageFallback(thumb, media);
        attachImageHoverPreview(thumb, card, prices);
        media.append(thumb);
      } else {
        media.append(createNoImagePlaceholder());
      }

      const contentWrap = el("div", { className: "ppo-result-content" });
      const topRow = el("div", { className: "ppo-result-toprow" });
      const details = el("div", { className: "ppo-result-details" });
      const favButton = el("button", {
        type: "button",
        className: favorites[card.putnam_card_id] ? "ppo-fav-button ppo-fav-active" : "ppo-fav-button",
        text: favorites[card.putnam_card_id] ? "★ FAVORITE" : "☆ FAVORITE"
      });
      favButton.addEventListener("click", async () => {
        await toggleFavorite(card);
        favButton.className = favorites[card.putnam_card_id] ? "ppo-fav-button ppo-fav-active" : "ppo-fav-button";
        favButton.textContent = favorites[card.putnam_card_id] ? "★ FAVORITE" : "☆ FAVORITE";
      });

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

      if (hasUsablePrices(prices)) {
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

      topRow.append(media, details, favButton);
      contentWrap.append(topRow, priceMount);
      row.append(contentWrap);
      resultsEl.append(row);
    }

    renderLoadMoreButton(payload);
  }

  function renderLoadMoreButton(payload) {
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

  function formatSuggestionSetName(value) {
    const raw = String(value || "").trim();
    if (raw.toLowerCase() === "151") return "SV: SCARLET & VIOLET 151";
    return raw.toUpperCase();
  }

  function clearSuggestions() {
    currentSuggestions = [];
    activeSuggestionIndex = -1;
    suggestionBox.replaceChildren();
    suggestionBox.classList.remove("ppo-suggestions-open");
  }

  function suggestionLabel(item) {
    const name = String(item.card_name || "UNKNOWN CARD").toUpperCase();
    const setName = formatSuggestionSetName(item.set_name || "UNKNOWN SET");
    const number = String(item.printed_number || "").toUpperCase();
    return `${name} • ${setName}${number ? ` • ${number}` : ""}`;
  }

  async function fetchSuggestions(query) {
    await loadSettings();

    const params = new URLSearchParams();
    params.set("q", query);
    params.set("limit", String(SUGGEST_LIMIT));

    const response = await fetch(`${backendUrl}/api/suggest?${params.toString()}`, { cache: "no-store" });
    const payload = await response.json();

    if (!payload?.ok) return [];
    return Array.isArray(payload.suggestions) ? payload.suggestions : [];
  }

  function renderSuggestions(items) {
    suggestionBox.replaceChildren();
    currentSuggestions = items || [];
    activeSuggestionIndex = -1;

    if (!currentSuggestions.length) {
      suggestionBox.classList.remove("ppo-suggestions-open");
      return;
    }

    for (const item of currentSuggestions) {
      const option = el("button", {
        type: "button",
        className: "ppo-suggestion-item",
        text: suggestionLabel(item)
      });

      option.addEventListener("click", () => {
        selectSuggestion(item);
      });

      suggestionBox.append(option);
    }

    suggestionBox.classList.add("ppo-suggestions-open");
  }

  function updateSuggestionActiveState() {
    const options = Array.from(suggestionBox.querySelectorAll(".ppo-suggestion-item"));
    options.forEach((option, index) => {
      option.classList.toggle("ppo-suggestion-active", index === activeSuggestionIndex);
    });
  }

  function selectSuggestion(item) {
    selectedSuggestion = item;
    queryInput.value = suggestionLabel(item);
    clearSuggestions();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  }

  function scheduleSuggestions() {
    selectedSuggestion = null;
    const value = queryInput.value.trim();

    if (suggestTimer) clearTimeout(suggestTimer);

    if (value.length < 2) {
      clearSuggestions();
      return;
    }

    suggestTimer = setTimeout(() => {
      fetchSuggestions(value)
        .then(renderSuggestions)
        .catch(() => clearSuggestions());
    }, 180);
  }

  async function loadSettings() {
    const response = await sendMessage({ type: "GET_LOOKUP_SETTINGS" });
    if (response?.backendUrl) backendUrl = response.backendUrl;
  }

  async function checkSearchServer() {
    await loadSettings();
    const response = await sendMessage({ type: "LOOKUP_HEALTH" });
    statusEl.textContent = response?.ok
      ? "Search ready. Enter name, set, or card number."
      : "Start start_watcher_backend.bat to enable lookup.";
  }

  async function search() {
    const rawQuery = queryInput.value.trim();
    const exactSelection = selectedSuggestion;

    clearSuggestions();

    if (!rawQuery && !exactSelection) {
      statusEl.textContent = "Enter a card name, set, or number.";
      resultsEl.replaceChildren();
      return;
    }

    await loadSettings();

    if (exactSelection?.putnam_card_id) {
      statusEl.textContent = "LOADING SELECTED CARD...";
      const payload = await fetchExactCard(exactSelection.putnam_card_id);

      currentSearchState = {
        query: exactSelection.card_name || rawQuery,
        setQuery: exactSelection.set_name || "",
        numberQuery: exactSelection.printed_number || "",
        nextOffset: 1,
        hasMore: false
      };

      selectedSuggestion = null;

      await saveSearchHistory(queryInput.value.trim());
      renderResults(payload.results || [], {
        append: false,
        payload,
        startingIndex: 0
      });
      return;
    }

    const query = rawQuery;
    const setQuery = "";
    const numberQuery = "";

    currentSearchState = {
      query,
      setQuery,
      numberQuery,
      nextOffset: 0,
      hasMore: false
    };

    selectedSuggestion = null;

    statusEl.textContent = "SEARCHING LOCAL POKEMON DATABASE...";
    await saveSearchHistory(query);
    const payload = await fetchSearchPage(query, setQuery, numberQuery, 0);

    currentSearchState.nextOffset = payload.next_offset || (payload.results || []).length;
    currentSearchState.hasMore = Boolean(payload.has_more);

    renderResults(payload.results || [], {
      append: false,
      payload,
      startingIndex: 0
    });
  }

  historyButton.addEventListener("click", () => renderQuickList("history"));
  favoritesButton.addEventListener("click", () => renderQuickList("favorites"));

  queryInput.addEventListener("input", scheduleSuggestions);

  queryInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      clearSuggestions();
      return;
    }

    if (event.key === "Enter") {
      if (currentSuggestions.length && activeSuggestionIndex >= 0) {
        event.preventDefault();
        selectSuggestion(currentSuggestions[activeSuggestionIndex]);
        return;
      }

      clearSuggestions();
      return;
    }

    if (!currentSuggestions.length) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeSuggestionIndex = Math.min(activeSuggestionIndex + 1, currentSuggestions.length - 1);
      updateSuggestionActiveState();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeSuggestionIndex = Math.max(activeSuggestionIndex - 1, 0);
      updateSuggestionActiveState();
    }
  });

  document.addEventListener("click", (event) => {
    if (!form.contains(event.target)) {
      clearSuggestions();
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearSuggestions();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  });

  loadUserLists().catch(() => {
    searchHistory = [];
    favorites = {};
  });

  checkSearchServer().catch(() => {
    statusEl.textContent = "Start start_watcher_backend.bat to enable lookup.";
  });
})();

