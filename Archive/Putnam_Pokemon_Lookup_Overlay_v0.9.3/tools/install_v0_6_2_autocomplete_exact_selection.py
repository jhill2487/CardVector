from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

ROOT = Path.cwd()
BACKEND = ROOT / "backend"
EXT = ROOT / "extension"

VIEWER = BACKEND / "viewer_server.py"
OVERLAY = EXT / "overlay.js"
MANIFEST = EXT / "manifest.json"
ARCHIVE = ROOT / "archive_old_versions"
NOTES = ROOT / "docs" / "release_notes"

ARCHIVE.mkdir(exist_ok=True)
NOTES.mkdir(parents=True, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

viewer = VIEWER.read_text(encoding="utf-8")
overlay = OVERLAY.read_text(encoding="utf-8")
manifest_text = MANIFEST.read_text(encoding="utf-8")

(ARCHIVE / f"viewer_server_before_v0_6_2_{stamp}.py").write_text(viewer, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_6_2_{stamp}.js").write_text(overlay, encoding="utf-8")
(ARCHIVE / f"manifest_before_v0_6_2_{stamp}.json").write_text(manifest_text, encoding="utf-8")

# Add exact card endpoint.
if 'if parsed.path == "/api/card":' not in viewer:
    marker = '        if parsed.path == "/api/search":'
    if marker not in viewer:
        raise SystemExit("ERROR: Could not find /api/search marker.")

    card_endpoint = '''        if parsed.path == "/api/card":
            putnam_card_id = params.get("id", [""])[0].strip()
            if not putnam_card_id:
                send_json(self, {"ok": False, "error": "Missing card id"}, 400)
                return

            card = get_card_by_id(putnam_card_id)
            if not card:
                send_json(self, {"ok": False, "error": "Card not found"}, 404)
                return

            card["thumbnail_url"] = f"/api/thumb-card?id={card['putnam_card_id']}"
            card["tcgplayer_search_url"] = tcgplayer_search_url(card)
            card["prices"] = None

            send_json(self, {
                "ok": True,
                "results": [card],
                "limit": 1,
                "offset": 0,
                "next_offset": 1,
                "has_more": False,
            })
            return

'''
    viewer = viewer.replace(marker, card_endpoint + marker)

# Add exact fetch helper.
if "async function fetchExactCard" not in overlay:
    marker = "  async function fetchSearchPage"
    if marker not in overlay:
        raise SystemExit("ERROR: Could not find fetchSearchPage marker.")

    helper = '''  async function fetchExactCard(putnamCardId) {
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

'''
    overlay = overlay.replace(marker, helper + marker)

# Replace search() with exact-card support for selected autocomplete item.
start = overlay.find("  async function search() {")
if start == -1:
    raise SystemExit("ERROR: Could not find search function.")

brace_start = overlay.find("{", start)
depth = 0
end = None

for i in range(brace_start, len(overlay)):
    if overlay[i] == "{":
        depth += 1
    elif overlay[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break

if end is None:
    raise SystemExit("ERROR: Could not parse search function.")

new_search = '''  async function search() {
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
    const payload = await fetchSearchPage(query, setQuery, numberQuery, 0);

    currentSearchState.nextOffset = payload.next_offset || (payload.results || []).length;
    currentSearchState.hasMore = Boolean(payload.has_more);

    renderResults(payload.results || [], {
      append: false,
      payload,
      startingIndex: 0
    });
  }'''

overlay = overlay[:start] + new_search + overlay[end:]

manifest = json.loads(manifest_text)
manifest["version"] = "0.6.2"

VIEWER.write_text(viewer, encoding="utf-8")
OVERLAY.write_text(overlay, encoding="utf-8")
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

(NOTES / "v0.6.2.md").write_text("""# Putnam Pokemon Lookup Overlay v0.6.2

## Fixed
- Autocomplete selection now loads the exact selected card by internal ID.
- Internal Putnam ID remains hidden from the user interface.
- Selecting suggestions no longer depends on fuzzy text search.

## Added
- Backend /api/card?id= endpoint for exact card retrieval.

## Version
- Chrome extension manifest updated to v0.6.2.
""", encoding="utf-8")

print("v0.6.2 installed.")
print("Autocomplete selections now load exact card records.")
print("Backend /api/card endpoint added.")
print("Manifest updated to v0.6.2.")
print("Backups saved to:", ARCHIVE)