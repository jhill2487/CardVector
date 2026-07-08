from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

ROOT = Path.cwd()
EXT = ROOT / "extension"
OVERLAY = EXT / "overlay.js"
CSS = EXT / "overlay.css"
MANIFEST = EXT / "manifest.json"
ARCHIVE = ROOT / "archive_old_versions"
NOTES = ROOT / "docs" / "release_notes"

ARCHIVE.mkdir(exist_ok=True)
NOTES.mkdir(parents=True, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

js = OVERLAY.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
manifest_text = MANIFEST.read_text(encoding="utf-8")

(ARCHIVE / f"overlay_before_v0_6_1_{stamp}.js").write_text(js, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_6_1_{stamp}.css").write_text(css, encoding="utf-8")
(ARCHIVE / f"manifest_before_v0_6_1_{stamp}.json").write_text(manifest_text, encoding="utf-8")

# Add selected suggestion state.
if "let selectedSuggestion = null;" not in js:
    js = js.replace(
        "  let currentSuggestions = [];",
        "  let currentSuggestions = [];\n  let selectedSuggestion = null;"
    )

# Clear selected suggestion when typing.
js = js.replace(
    '  function scheduleSuggestions() {\n    const value = queryInput.value.trim();',
    '''  function scheduleSuggestions() {
    selectedSuggestion = null;
    const value = queryInput.value.trim();'''
)

# Replace selectSuggestion so input displays cleanly but search uses structured fields.
old_select = '''  function selectSuggestion(item) {
    queryInput.value = suggestionLabel(item).replace(/ • /g, " ");
    clearSuggestions();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  }
'''

new_select = '''  function selectSuggestion(item) {
    selectedSuggestion = item;
    queryInput.value = suggestionLabel(item);
    clearSuggestions();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  }
'''

if old_select not in js:
    raise SystemExit("ERROR: Could not find selectSuggestion block. No changes written.")
js = js.replace(old_select, new_select)

# Replace search query parsing to use structured suggestion values.
old_search_start = '''  async function search() {
    const rawQuery = queryInput.value.trim();
    const query = rawQuery;
    const setQuery = "";
    const numberQuery = "";

    clearSuggestions();

    if (!query) {
'''

new_search_start = '''  async function search() {
    const rawQuery = queryInput.value.trim();
    const query = selectedSuggestion?.card_name || rawQuery;
    const setQuery = selectedSuggestion?.set_name || "";
    const numberQuery = selectedSuggestion?.printed_number || "";

    clearSuggestions();

    if (!query) {
'''

if old_search_start not in js:
    raise SystemExit("ERROR: Could not find search() query parsing block. No changes written.")
js = js.replace(old_search_start, new_search_start)

# Reset selected suggestion after currentSearchState is created so future manual edits are not stuck.
js = js.replace(
    '''    currentSearchState = {
      query,
      setQuery,
      numberQuery,
      nextOffset: 0,
      hasMore: false
    };
''',
    '''    currentSearchState = {
      query,
      setQuery,
      numberQuery,
      nextOffset: 0,
      hasMore: false
    };

    selectedSuggestion = null;
'''
)

# Make autocomplete dropdown less intrusive.
if "v0.6.1 - Autocomplete UX Fix" not in css:
    css += r'''

/* v0.6.1 - Autocomplete UX Fix */
.ppo-suggestions {
  max-height: 150px !important;
  font-size: 10px !important;
}

.ppo-suggestion-item {
  padding: 7px 9px !important;
  line-height: 1.2 !important;
}

.ppo-suggestions-open {
  max-height: min(150px, 35vh) !important;
}
'''

manifest = json.loads(manifest_text)
manifest["version"] = "0.6.1"

OVERLAY.write_text(js, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

(NOTES / "v0.6.1.md").write_text("""# Putnam Pokemon Lookup Overlay v0.6.1

## Fixed
- Selecting an autocomplete suggestion now searches using structured card fields instead of the full display label.
- Autocomplete dropdown height reduced so it does not cover most search results.

## Improved
- Autocomplete selection keeps Putnam IDs hidden from the UI.
- Search dropdown closes cleanly when a search runs.

## Version
- Chrome extension manifest updated to v0.6.1.
""", encoding="utf-8")

print("v0.6.1 installed.")
print("Fixed autocomplete selection search behavior.")
print("Reduced autocomplete dropdown height.")
print("Manifest updated to v0.6.1.")
print("Backups saved to:", ARCHIVE)