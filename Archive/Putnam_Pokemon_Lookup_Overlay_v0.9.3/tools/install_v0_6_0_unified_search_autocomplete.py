from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

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

(ARCHIVE / f"viewer_server_before_v0_6_0_{stamp}.py").write_text(viewer, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_6_0_{stamp}.js").write_text(overlay, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_6_0_{stamp}.css").write_text(css, encoding="utf-8")
(ARCHIVE / f"manifest_before_v0_6_0_{stamp}.json").write_text(manifest_text, encoding="utf-8")


def replace_function(source: str, function_name: str, new_function: str) -> str:
    candidates = [
        f"  async function {function_name}(",
        f"  function {function_name}(",
    ]
    start = -1
    for marker in candidates:
        start = source.find(marker)
        if start != -1:
            break

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
# Backend: /api/suggest endpoint
# ----------------------------
if 'if parsed.path == "/api/suggest":' not in viewer:
    search_marker = '        if parsed.path == "/api/search":'
    if search_marker not in viewer:
        raise SystemExit("ERROR: Could not find /api/search marker in viewer_server.py.")

    suggest_block = '''        if parsed.path == "/api/suggest":
            query = params.get("q", [""])[0].strip()
            if not query:
                send_json(self, {"ok": True, "suggestions": []})
                return

            try:
                limit = int(params.get("limit", ["10"])[0] or 10)
            except ValueError:
                limit = 10

            limit = max(1, min(limit, 20))

            suggestions = []
            for card in search_cards(name=query, limit=limit):
                suggestions.append({
                    "card_name": card.get("card_name") or card.get("name") or "",
                    "set_name": card.get("set_name") or card.get("set") or "",
                    "printed_number": card.get("printed_number") or card.get("card_number") or card.get("number") or "",
                    "putnam_card_id": card.get("putnam_card_id") or "",
                })

            send_json(self, {
                "ok": True,
                "query": query,
                "suggestions": suggestions,
            })
            return

'''
    viewer = viewer.replace(search_marker, suggest_block + search_marker)


# ----------------------------
# Overlay: add v0.6 globals
# ----------------------------
if "SUGGEST_LIMIT" not in overlay:
    overlay = overlay.replace(
        '  let currentSearchState = null;',
        '''  let currentSearchState = null;
  const SUGGEST_LIMIT = 10;
  let suggestTimer = null;
  let activeSuggestionIndex = -1;
  let currentSuggestions = [];'''
    )


# ----------------------------
# Overlay: replace search fields with unified field
# ----------------------------
old_form = '''  const queryInput = el("input", { id: "ppo-query", type: "search", placeholder: "Card name, e.g. Watchog" });
  const setInput = el("input", { id: "ppo-set", type: "search", placeholder: "Set" });
  const numberInput = el("input", { id: "ppo-number", type: "search", placeholder: "No." });
  const submitButton = el("button", { type: "submit", text: "Search" });
  const form = el("form", { id: "ppo-search-form" }, [
    queryInput,
    el("div", { className: "ppo-filter-row" }, [setInput, numberInput]),
    submitButton
  ]);
'''

new_form = '''  const queryInput = el("input", {
    id: "ppo-query",
    type: "search",
    placeholder: "Search card, set, or number..."
  });
  const suggestionBox = el("div", { id: "ppo-suggestions", className: "ppo-suggestions" });
  const submitButton = el("button", { type: "submit", text: "Search" });
  const form = el("form", { id: "ppo-search-form" }, [
    el("div", { className: "ppo-unified-search-wrap" }, [queryInput, suggestionBox]),
    submitButton
  ]);
'''

if old_form not in overlay:
    raise SystemExit("ERROR: Could not find existing 3-field search form block in overlay.js.")

overlay = overlay.replace(old_form, new_form)


# ----------------------------
# Overlay: autocomplete helpers before loadSettings
# ----------------------------
if "async function fetchSuggestions" not in overlay:
    marker = "  async function loadSettings() {"
    if marker not in overlay:
        raise SystemExit("ERROR: Could not find loadSettings insertion point.")

    autocomplete_code = '''  function formatSuggestionSetName(value) {
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
    queryInput.value = suggestionLabel(item).replace(/ • /g, " ");
    clearSuggestions();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  }

  function scheduleSuggestions() {
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

'''
    overlay = overlay.replace(marker, autocomplete_code + marker)


# ----------------------------
# Overlay: replace search() for unified query
# ----------------------------
new_search = '''  async function search() {
    const rawQuery = queryInput.value.trim();
    const query = rawQuery;
    const setQuery = "";
    const numberQuery = "";

    clearSuggestions();

    if (!query) {
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
# Overlay: add suggestion event listeners before form submit listener
# ----------------------------
if "queryInput.addEventListener(\"input\", scheduleSuggestions);" not in overlay:
    marker = '''  form.addEventListener("submit", (event) => {'''
    if marker not in overlay:
        raise SystemExit("ERROR: Could not find form submit listener marker.")

    events = '''  queryInput.addEventListener("input", scheduleSuggestions);

  queryInput.addEventListener("keydown", (event) => {
    if (!currentSuggestions.length) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeSuggestionIndex = Math.min(activeSuggestionIndex + 1, currentSuggestions.length - 1);
      updateSuggestionActiveState();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeSuggestionIndex = Math.max(activeSuggestionIndex - 1, 0);
      updateSuggestionActiveState();
    } else if (event.key === "Enter" && activeSuggestionIndex >= 0) {
      event.preventDefault();
      selectSuggestion(currentSuggestions[activeSuggestionIndex]);
    } else if (event.key === "Escape") {
      clearSuggestions();
    }
  });

  document.addEventListener("click", (event) => {
    if (!form.contains(event.target)) {
      clearSuggestions();
    }
  });

'''
    overlay = overlay.replace(marker, events + marker)


# ----------------------------
# CSS
# ----------------------------
if "v0.6.0 - Unified Search and Autocomplete" not in css:
    css += r'''

/* v0.6.0 - Unified Search and Autocomplete */
.ppo-unified-search-wrap {
  position: relative;
  width: 100%;
}

.ppo-suggestions {
  display: none;
  position: absolute;
  z-index: 2147483647;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 260px;
  overflow-y: auto;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.28);
}

.ppo-suggestions-open {
  display: block;
}

.ppo-suggestion-item {
  width: 100%;
  display: block;
  text-align: left;
  padding: 9px 10px;
  border: 0;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
  color: #111827;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}

.ppo-suggestion-item:last-child {
  border-bottom: 0;
}

.ppo-suggestion-item:hover,
.ppo-suggestion-active {
  background: #eff6ff;
  color: #0f172a;
}

#ppo-query {
  text-transform: none;
}
'''


# ----------------------------
# Manifest + release notes
# ----------------------------
manifest = json.loads(manifest_text)
manifest["version"] = "0.6.0"

VIEWER.write_text(viewer, encoding="utf-8")
OVERLAY.write_text(overlay, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

(NOTES / "v0.6.0.md").write_text("""# Putnam Pokemon Lookup Overlay v0.6.0

## Added
- Unified single search bar.
- Autocomplete suggestions.
- Suggestion display includes card name, set name, and card number.
- Keyboard navigation for autocomplete: Arrow Up, Arrow Down, Enter, Escape.
- Backend /api/suggest endpoint.

## Removed
- Separate Set and No. input fields from the overlay UI.

## Improved
- Search experience is simpler and closer to public-product behavior.
- Internal Putnam IDs remain hidden from the user interface.

## Version
- Chrome extension manifest updated to v0.6.0.
""", encoding="utf-8")

print("v0.6.0 installed.")
print("Added unified search bar and autocomplete suggestions.")
print("Manifest updated to v0.6.0.")
print("Backups saved to:", ARCHIVE)