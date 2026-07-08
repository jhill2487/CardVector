(function () {
  const existing = document.getElementById("putnam-pokemon-overlay");
  if (existing) return;

  let backendUrl = "http://127.0.0.1:8790";

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

  function renderVariantPrices(card, prices) {
    const variants = Array.isArray(prices?.variants) ? prices.variants : [];
    if (!variants.length) {
      const nm = pickPrice(prices, ["NM", "near_mint", "Near Mint"]);
      const lp = pickPrice(prices, ["LP", "lightly_played", "Lightly Played"]);
      const market = pickPrice(prices, ["MARKET", "market", "raw"]);
      const priceText = nm || lp
        ? `${nm ? `NM ${nm}` : ""}${nm && lp ? " / " : ""}${lp ? `LP ${lp}` : ""}`
        : market
          ? `Market ${market}`
          : "No live price";

      return el("div", {
        className: `ppo-price-badge ${nm || lp || market ? "" : "ppo-muted-price"}`,
        text: priceText
      });
    }

    const wrap = el("div", { className: "ppo-variant-wrap" });
    wrap.append(el("div", { className: "ppo-variant-title", text: "Market variants" }));

    for (const variant of variants) {
      const row = el("div", { className: "ppo-variant-row" });
      const imgUrl = absoluteUrl(variant.image_url || card.thumbnail_url || card.image_url || card.small_image_url);

      if (imgUrl) {
        row.append(el("img", {
          className: "ppo-variant-thumb",
          attrs: { src: imgUrl, alt: variantLabel(variant), loading: "lazy" }
        }));
      }

      const main = el("div", { className: "ppo-variant-main" });
      main.append(el("div", { className: "ppo-variant-name", text: variantLabel(variant) }));

      const table = el("div", { className: "ppo-price-grid" }, [
        el("span", { text: "NM" }),
        el("strong", { text: conditionCell(variant.conditions, "NM") }),
        el("span", { text: "LP" }),
        el("strong", { text: conditionCell(variant.conditions, "LP") }),
        el("span", { text: "MP" }),
        el("strong", { text: conditionCell(variant.conditions, "MP") })
      ]);

      main.append(table);

      if (variant.tcgplayer_url) {
        const link = el("a", {
          className: "ppo-tcg-link",
          text: "Open TCGplayer",
          attrs: { href: variant.tcgplayer_url, target: "_blank", rel: "noopener noreferrer" }
        });
        main.append(link);
      }

      row.append(main);
      wrap.append(row);
    }

    return wrap;
  }

  const root = el("div", { id: "putnam-pokemon-overlay" });
  const title = el("strong", { text: "Pokemon Lookup" });
  const toggleButton = el("button", { id: "ppo-toggle", type: "button", title: "Collapse", text: "-" });
  const closeButton = el("button", { id: "ppo-close", type: "button", title: "Close", text: "x" });
  const header = el("div", { className: "ppo-header" }, [title, el("div", { className: "ppo-actions" }, [toggleButton, closeButton])]);

  const queryInput = el("input", { id: "ppo-query", type: "search", placeholder: "Card name, e.g. Watchog" });
  const setInput = el("input", { id: "ppo-set", type: "search", placeholder: "Set" });
  const numberInput = el("input", { id: "ppo-number", type: "search", placeholder: "No." });
  const submitButton = el("button", { type: "submit", text: "Search" });
  const form = el("form", { id: "ppo-search-form" }, [
    queryInput,
    el("div", { className: "ppo-filter-row" }, [setInput, numberInput]),
    submitButton
  ]);
  const statusEl = el("div", { id: "ppo-status", text: "Checking local lookup server..." });
  const resultsEl = el("div", { id: "ppo-results" });
  const body = el("div", { className: "ppo-body" }, [form, statusEl, resultsEl]);

  root.append(header, body);
  document.documentElement.appendChild(root);

  closeButton.addEventListener("click", () => root.remove());
  toggleButton.addEventListener("click", () => {
    const collapsed = root.classList.toggle("ppo-collapsed");
    toggleButton.textContent = collapsed ? "+" : "-";
    body.hidden = collapsed;
  });

  function renderResults(results) {
    resultsEl.replaceChildren();

    if (!results.length) {
      statusEl.textContent = "No matches. Try name + card number, or set + number.";
      return;
    }

    statusEl.textContent = `${results.length} match${results.length === 1 ? "" : "es"}`;
    for (const card of results) {
      const row = el("div", { className: "ppo-result" });
      const prices = card.prices || {};

      const media = el("div", { className: "ppo-media" });
      const imageUrl = absoluteUrl(card.thumbnail_url || card.image_url || card.small_image_url || prices?.variants?.[0]?.image_url);
      if (imageUrl) {
        const thumb = el("img", {
          className: "ppo-thumb",
          attrs: { src: imageUrl, alt: card.card_name || "Pokemon card image", loading: "lazy" }
        });
        media.append(thumb);
      }

      const details = el("div", { className: "ppo-result-details" });
      details.append(
        el("strong", { text: card.card_name || card.name || "Unknown card" }),
        el("span", { text: `${card.set_name || card.set || "Unknown set"} ${card.printed_number || card.card_number || card.number || ""}`.trim() }),
        el("span", { text: card.rarity ? `Rarity: ${card.rarity}` : "" }),
        el("span", { text: card.confidence ? `Database match: ${Math.round(Number(card.confidence) * 100)}%` : "" })
      );

      if (prices?.source || card.price_source) {
        details.append(el("span", { className: "ppo-price-source", text: `Price source: ${prices.source || card.price_source}` }));
      }

      details.append(renderVariantPrices(card, prices));

      row.append(media, details);
      resultsEl.append(row);
    }
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
    const query = queryInput.value.trim();
    const setQuery = setInput.value.trim();
    const numberQuery = numberInput.value.trim();

    if (!query && !setQuery && !numberQuery) {
      statusEl.textContent = "Enter a card name, set, or number.";
      resultsEl.replaceChildren();
      return;
    }

    statusEl.textContent = "Searching local Pokemon database...";
    const response = await sendMessage({
      type: "OVERLAY_SEARCH",
      query,
      setQuery,
      numberQuery,
      conditions: "NM,LP"
    });

    if (chrome.runtime.lastError) {
      statusEl.textContent = chrome.runtime.lastError.message;
      return;
    }

    if (!response?.ok) {
      statusEl.textContent = response?.error || "Search failed. Is start_watcher_backend.bat running?";
      return;
    }
    renderResults(response.results || []);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  });

  checkSearchServer().catch(() => {
    statusEl.textContent = "Start start_watcher_backend.bat to enable lookup.";
  });
})();
