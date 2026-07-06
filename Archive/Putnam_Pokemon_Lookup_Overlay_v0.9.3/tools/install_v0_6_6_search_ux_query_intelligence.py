from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]

JS = ROOT / "extension" / "overlay.js"
CATALOG = ROOT / "backend" / "card_catalog.py"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, CATALOG, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_6_{stamp}{p.suffix}")

# -------------------------
# Frontend Search UX patch
# -------------------------
js = JS.read_text(encoding="utf-8")

old_keydown = '''  queryInput.addEventListener("keydown", (event) => {
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
  });'''

new_keydown = '''  queryInput.addEventListener("keydown", (event) => {
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
  });'''

if old_keydown not in js:
    raise SystemExit("ERROR: Could not find keydown handler. No changes written.")

js = js.replace(old_keydown, new_keydown, 1)

old_submit = '''  form.addEventListener("submit", (event) => {
    event.preventDefault();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  });'''

new_submit = '''  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearSuggestions();
    search().catch((error) => {
      statusEl.textContent = error.message || "Search failed.";
    });
  });'''

if old_submit not in js:
    raise SystemExit("ERROR: Could not find form submit handler. No changes written.")

js = js.replace(old_submit, new_submit, 1)
JS.write_text(js, encoding="utf-8")

# -------------------------
# Backend Query Intelligence
# -------------------------
catalog = CATALOG.read_text(encoding="utf-8")

if "v0.6.6 search ux query intelligence" not in catalog:
    patch = r'''

# v0.6.6 search ux query intelligence
# Collector-style query upgrades without changing UI:
# base charizard / charizard base
# 151 pikachu / pikachu 151
# reverse holo pikachu / holo dark charizard
# shadowless / first edition / unlimited hints remain compatible with previous parser patches.

def _v066_query_norm(value):
    import re
    return re.sub(r"[^a-z0-9/]+", " ", str(value or "").lower()).strip()


def _v066_strip_finish_terms(query):
    tokens = _v066_query_norm(query).split()
    finish_terms = {
        "reverse", "holo", "holofoil", "foil",
        "normal", "cosmos", "stamped", "stamp",
    }
    return " ".join(t for t in tokens if t not in finish_terms).strip()


def _v066_finish_hint(query):
    q = _v066_query_norm(query)
    if "reverse holo" in q or "reverse" in q:
        return "reverse_holo"
    if "cosmos" in q:
        return "cosmos_holo"
    if "holo" in q or "holofoil" in q:
        return "holo"
    if "normal" in q:
        return "normal"
    return ""


try:
    _v066_previous_parse_query = _v064c_parse_query
except NameError:
    _v066_previous_parse_query = None


def _v064c_parse_query(query):
    if _v066_previous_parse_query is None:
        return {
            "original": str(query or "").strip(),
            "name": str(query or "").strip(),
            "set": "",
            "number": "",
            "variant": "",
            "attempts": [{"name": str(query or "").strip(), "number": None, "set_slug_or_name": None}],
        }

    original = str(query or "").strip()
    q = _v066_query_norm(original)
    stripped = _v066_strip_finish_terms(original)

    parsed = _v066_previous_parse_query(stripped or original)

    finish_hint = _v066_finish_hint(original)
    if finish_hint:
        parsed["finish_hint"] = finish_hint
        if not parsed.get("variant"):
            parsed["variant"] = finish_hint

    # Standalone collector set aliases that earlier parser versions may miss.
    tokens = q.split()

    if "base" in tokens and not parsed.get("set"):
        parsed["set"] = "base"
        parsed["name"] = " ".join(t for t in tokens if t != "base").strip()

    if "151" in tokens and not parsed.get("set"):
        parsed["set"] = "151"
        parsed["name"] = " ".join(t for t in tokens if t != "151").strip()

    # Rebuild attempts when we added or corrected set/name.
    attempts = []

    def add_attempt(name=None, number=None, set_name=None):
        attempt = {
            "name": name or None,
            "number": number or None,
            "set_slug_or_name": set_name or None,
        }
        if attempt not in attempts:
            attempts.append(attempt)

    name = parsed.get("name") or ""
    number = parsed.get("number") or ""
    set_name = parsed.get("set") or ""

    if name and number and set_name:
        add_attempt(name, number, set_name)
    if name and set_name:
        add_attempt(name, None, set_name)
    if name and number:
        add_attempt(name, number, None)
    if number and set_name:
        add_attempt(None, number, set_name)
    if number:
        add_attempt(None, number, None)
    if name:
        add_attempt(name, None, None)
    add_attempt(stripped or original, None, None)

    parsed["attempts"] = attempts
    parsed["original"] = original

    return parsed
'''
    catalog = catalog.rstrip() + "\n" + patch + "\n"

CATALOG.write_text(catalog, encoding="utf-8")

# -------------------------
# Version bump
# -------------------------
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.6"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.6 Search UX & Query Intelligence")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - backend/card_catalog.py")
print(" - extension/manifest.json")