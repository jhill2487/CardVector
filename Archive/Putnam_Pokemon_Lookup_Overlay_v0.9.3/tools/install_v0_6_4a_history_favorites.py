from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"

overlay_js = EXT / "overlay.js"
overlay_css = EXT / "overlay.css"
manifest = EXT / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [overlay_js, overlay_css, manifest]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_4a_{stamp}{p.suffix}")

js = overlay_js.read_text(encoding="utf-8")

if "v0.6.4A history/favorites" not in js:
    js = js.replace(
        "  let selectedSuggestion = null;",
        """  let selectedSuggestion = null;

  // v0.6.4A history/favorites
  const HISTORY_KEY = "putnamLookupSearchHistory";
  const FAVORITES_KEY = "putnamLookupFavorites";
  const HISTORY_LIMIT = 20;
  let searchHistory = [];
  let favorites = {};"""
    )

    js = js.replace(
        '  const suggestionBox = el("div", { id: "ppo-suggestions", className: "ppo-suggestions" });',
        '''  const suggestionBox = el("div", { id: "ppo-suggestions", className: "ppo-suggestions" });
  const quickBar = el("div", { className: "ppo-quickbar" });
  const historyButton = el("button", { type: "button", className: "ppo-mini-button", text: "RECENT" });
  const favoritesButton = el("button", { type: "button", className: "ppo-mini-button", text: "FAVORITES" });
  const quickList = el("div", { className: "ppo-quicklist" });
  quickBar.append(historyButton, favoritesButton, quickList);'''
    )

    js = js.replace(
        '  const body = el("div", { className: "ppo-body" }, [form, statusEl, resultsEl]);',
        '  const body = el("div", { className: "ppo-body" }, [form, quickBar, statusEl, resultsEl]);'
    )

    js = js.replace(
        "  function renderResults(results, options = {}) {",
        r'''  function storageGet(keys) {
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

  function renderResults(results, options = {}) {'''
    )

    js = js.replace(
        '      const details = el("div", { className: "ppo-result-details" });',
        '''      const details = el("div", { className: "ppo-result-details" });
      const favButton = el("button", {
        type: "button",
        className: favorites[card.putnam_card_id] ? "ppo-fav-button ppo-fav-active" : "ppo-fav-button",
        text: favorites[card.putnam_card_id] ? "★ FAVORITE" : "☆ FAVORITE"
      });
      favButton.addEventListener("click", async () => {
        await toggleFavorite(card);
        favButton.className = favorites[card.putnam_card_id] ? "ppo-fav-button ppo-fav-active" : "ppo-fav-button";
        favButton.textContent = favorites[card.putnam_card_id] ? "★ FAVORITE" : "☆ FAVORITE";
      });'''
    )

    js = js.replace(
        '      details.append(\n        el("strong", { text: String(card.card_name || card.name || "UNKNOWN CARD").toUpperCase() }),',
        '      details.append(\n        favButton,\n        el("strong", { text: String(card.card_name || card.name || "UNKNOWN CARD").toUpperCase() }),'
    )

    js = js.replace(
        '      renderResults(payload.results || [], {',
        '      await saveSearchHistory(queryInput.value.trim());\n      renderResults(payload.results || [], {',
        1
    )

    js = js.replace(
        '    const payload = await fetchSearchPage(query, setQuery, numberQuery, 0);',
        '    await saveSearchHistory(query);\n    const payload = await fetchSearchPage(query, setQuery, numberQuery, 0);'
    )

    js = js.replace(
        '  queryInput.addEventListener("input", scheduleSuggestions);',
        '''  historyButton.addEventListener("click", () => renderQuickList("history"));
  favoritesButton.addEventListener("click", () => renderQuickList("favorites"));

  queryInput.addEventListener("input", scheduleSuggestions);'''
    )

    js = js.replace(
        '  checkSearchServer().catch(() => {',
        '''  loadUserLists().catch(() => {
    searchHistory = [];
    favorites = {};
  });

  checkSearchServer().catch(() => {'''
    )

overlay_js.write_text(js, encoding="utf-8")

css = overlay_css.read_text(encoding="utf-8")
if "v0.6.4A history/favorites" not in css:
    css += r'''

/* v0.6.4A history/favorites */
.ppo-quickbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0;
}

.ppo-mini-button,
.ppo-fav-button,
.ppo-quick-item {
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 8px;
  padding: 5px 8px;
  font-size: 11px;
  cursor: pointer;
}

.ppo-quicklist {
  display: none;
  width: 100%;
  max-height: 160px;
  overflow: auto;
  border-radius: 10px;
  padding: 6px;
  background: rgba(0,0,0,0.18);
}

.ppo-quicklist-open {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ppo-quick-item {
  text-align: left;
}

.ppo-quick-empty {
  font-size: 12px;
  opacity: 0.75;
  padding: 6px;
}

.ppo-fav-button {
  align-self: flex-start;
  margin-bottom: 4px;
}

.ppo-fav-active {
  font-weight: 700;
}
'''
overlay_css.write_text(css, encoding="utf-8")

mj = manifest.read_text(encoding="utf-8")
mj = mj.replace('"version": "0.6.3"', '"version": "0.6.4"')
manifest.write_text(mj, encoding="utf-8")

print("Installed v0.6.4A Search History + Favorites")
print(f"Backups saved in: {archive}")
print("Files patched:")
print(" - extension/overlay.js")
print(" - extension/overlay.css")
print(" - extension/manifest.json")