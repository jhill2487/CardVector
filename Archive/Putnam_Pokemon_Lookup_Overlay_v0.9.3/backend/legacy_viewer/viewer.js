const statusUrl = "runtime/status.json";
const catalogStatusUrl = "runtime/catalog_status.json";
const frameUrl = "runtime/latest_frame.jpg";

const healthEl = document.getElementById("health");
const noteEl = document.getElementById("note");
const cardNameEl = document.getElementById("cardName");
const confidenceEl = document.getElementById("confidence");
const priceRowsEl = document.getElementById("priceRows");
const setCountEl = document.getElementById("setCount");
const cardCountEl = document.getElementById("cardCount");
const fingerprintCountEl = document.getElementById("fingerprintCount");
const visualCountEl = document.getElementById("visualCount");
const candidateRowsEl = document.getElementById("candidateRows");
const searchForm = document.getElementById("searchForm");
const searchQueryEl = document.getElementById("searchQuery");
const searchSetEl = document.getElementById("searchSet");
const searchNumberEl = document.getElementById("searchNumber");
const searchStatusEl = document.getElementById("searchStatus");
const searchResultsEl = document.getElementById("searchResults");

const conditionOrder = [
  "NM",
  "LP"
];

function money(value) {
  if (typeof value !== "number") return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function renderPrices(prices) {
  priceRowsEl.innerHTML = "";

  if (!prices) {
    priceRowsEl.textContent = "No price ladder loaded.";
    return;
  }

  for (const key of conditionOrder) {
    const price = prices[key];
    if (!price) continue;

    const row = document.createElement("div");
    row.className = "price-row";
    row.innerHTML = `
      <div class="condition">${key}</div>
      <div class="range">${money(price.low)} - ${money(price.high)}</div>
      <div class="market">${money(price.market)}</div>
    `;
    priceRowsEl.appendChild(row);
  }
}

function renderCatalog(catalog) {
  setCountEl.textContent = String(catalog?.sets || 0);
  cardCountEl.textContent = String(catalog?.cards || 0);
  fingerprintCountEl.textContent = String(catalog?.fingerprints || 0);
  visualCountEl.textContent = String(catalog?.visual_index_rows || 0);
}

function renderCandidates(candidates) {
  candidateRowsEl.innerHTML = "";

  if (!candidates || !candidates.length) {
    candidateRowsEl.textContent = "No candidates yet.";
    return;
  }

  for (const card of candidates.slice(0, 5)) {
    const row = document.createElement("div");
    row.className = "candidate-row";

    if (card.putnam_card_id) {
      const thumbnail = document.createElement("img");
      thumbnail.alt = "";
      thumbnail.className = "result-thumb";
      thumbnail.src = `/api/thumb-card?id=${encodeURIComponent(card.putnam_card_id)}`;
      row.classList.add("with-thumb");
      row.appendChild(thumbnail);
    }

    const details = document.createElement("div");
    details.className = "result-details";
    details.innerHTML = `
      <strong>${card.card_name || "Unknown card"}</strong>
      <span>${card.set_name || "Unknown set"} ${card.printed_number || card.card_number || ""}</span>
    `;
    row.appendChild(details);
    candidateRowsEl.appendChild(row);
  }
}

function renderSearchResults(results) {
  searchResultsEl.innerHTML = "";

  if (!results.length) {
    searchStatusEl.textContent = "No matches.";
    return;
  }

  searchStatusEl.textContent = `${results.length} match${results.length === 1 ? "" : "es"}`;

  for (const card of results) {
    const row = document.createElement("div");
    row.className = "search-result";

    const prices = card.prices || {};
    const nm = prices.NM?.market;
    const lp = prices.LP?.market;
    const genericMarket = prices.MARKET?.market;
    const priceText = nm || lp
      ? `${nm ? `NM $${Math.round(nm)}` : ""}${nm && lp ? " / " : ""}${lp ? `LP $${Math.round(lp)}` : ""}`
      : genericMarket
        ? `Market $${Math.round(genericMarket)}`
        : "No price";

    const media = document.createElement("div");
    media.className = "result-media";

    const thumbnail = document.createElement("img");
    thumbnail.alt = "";
    thumbnail.className = "result-thumb";
    if (card.thumbnail_url) thumbnail.src = card.thumbnail_url;

    const priceBadge = document.createElement("div");
    priceBadge.className = `price-badge ${nm || lp || genericMarket ? "" : "muted-price"}`;
    priceBadge.textContent = priceText;
    media.append(thumbnail, priceBadge);

    const details = document.createElement("div");
    details.className = "result-details";
    details.innerHTML = `
      <strong>${card.card_name || "Unknown card"}</strong>
      <span>${card.set_name || "Unknown set"} ${card.printed_number || card.card_number || ""}</span>
      ${genericMarket && !nm && !lp ? `<span class="price-source">${prices.MARKET.provider || "fallback"} fallback</span>` : ""}
    `;

    row.append(media, details);
    searchResultsEl.appendChild(row);
  }
}

async function runSearch() {
  const query = searchQueryEl.value.trim();
  const setQuery = searchSetEl.value.trim();
  const numberQuery = searchNumberEl.value.trim();

  if (!query && !setQuery && !numberQuery) {
    searchStatusEl.textContent = "Enter a card name, set, or number.";
    searchResultsEl.innerHTML = "";
    return;
  }

  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (setQuery) params.set("set", setQuery);
  if (numberQuery) params.set("number", numberQuery);

  searchStatusEl.textContent = "Searching...";
  const response = await fetch(`/api/search?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Search server not running. Close and reopen open_viewer.bat.");
  }
  const payload = await response.json();
  renderSearchResults(payload.results || []);
}

async function loadCatalogFallback() {
  const response = await fetch(`${catalogStatusUrl}?t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) return null;
  return response.json();
}

async function refresh() {
  try {
    const response = await fetch(`${statusUrl}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Status unavailable");

    const status = await response.json();
    healthEl.textContent = "Live";
    noteEl.textContent = status.note || "Capture running.";
    cardNameEl.textContent = status.latest_card_name || "No card detected";
    confidenceEl.textContent = `Confidence ${Math.round((status.confidence || 0) * 100)}%`;
    renderPrices(status.prices);
    renderCatalog(status.catalog || await loadCatalogFallback());
    renderCandidates(status.candidates);

  } catch (error) {
    healthEl.textContent = "Waiting";
    noteEl.textContent = "Open the Chrome monitor and start tab capture.";
    try {
      renderCatalog(await loadCatalogFallback());
    } catch {
      renderCatalog(null);
    }
  }
}

refresh();
setInterval(refresh, 1000);

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await runSearch();
  } catch (error) {
    searchStatusEl.textContent = error.message || "Search failed.";
  }
});
