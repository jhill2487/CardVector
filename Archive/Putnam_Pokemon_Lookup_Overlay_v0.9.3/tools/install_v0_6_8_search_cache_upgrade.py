from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend" / "card_catalog.py"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [CATALOG, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_8_{stamp}{p.suffix}")

text = CATALOG.read_text(encoding="utf-8")

if "v0.6.8 search cache upgrade" not in text:
    patch = r'''

# v0.6.8 search cache upgrade
# Short-lived backend cache for repeated live-stream searches.
# No search behavior changes; only avoids recomputing identical queries.

import time as _v068_time

_V068_SEARCH_CACHE_TTL_SECONDS = 300
_V068_SEARCH_CACHE_MAX_ITEMS = 256
_v068_search_cache = {}

try:
    _v068_previous_search_cards = search_cards
except NameError:
    _v068_previous_search_cards = None


def _v068_search_cache_key(name=None, number=None, set_slug_or_name=None, limit=20):
    return (
        str(name or "").strip().lower(),
        str(number or "").strip().lower(),
        str(set_slug_or_name or "").strip().lower(),
        int(limit or 20),
    )


def _v068_cache_get(key):
    item = _v068_search_cache.get(key)
    if not item:
        return None

    created_at, value = item
    if _v068_time.time() - created_at > _V068_SEARCH_CACHE_TTL_SECONDS:
        _v068_search_cache.pop(key, None)
        return None

    # Return shallow copies so callers can safely add thumbnail/prices fields.
    return [dict(row) for row in value]


def _v068_cache_set(key, value):
    if len(_v068_search_cache) >= _V068_SEARCH_CACHE_MAX_ITEMS:
        oldest = sorted(_v068_search_cache.items(), key=lambda item: item[1][0])[:32]
        for old_key, _ in oldest:
            _v068_search_cache.pop(old_key, None)

    _v068_search_cache[key] = (_v068_time.time(), [dict(row) for row in (value or [])])


def clear_search_cache():
    _v068_search_cache.clear()


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    key = _v068_search_cache_key(name=name, number=number, set_slug_or_name=set_slug_or_name, limit=limit)

    cached = _v068_cache_get(key)
    if cached is not None:
        for row in cached:
            row["_search_cache_hit"] = True
        return cached

    rows = _v068_previous_search_cards(
        name=name,
        number=number,
        set_slug_or_name=set_slug_or_name,
        limit=limit,
    ) if _v068_previous_search_cards else []

    _v068_cache_set(key, rows)

    return rows


try:
    _v068_previous_write_catalog_status = write_catalog_status

    def write_catalog_status():
        clear_search_cache()
        return _v068_previous_write_catalog_status()
except NameError:
    pass
'''
    text = text.rstrip() + "\n" + patch + "\n"

CATALOG.write_text(text, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.8"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.8 Search Cache Upgrade")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - backend/card_catalog.py")
print(" - extension/manifest.json")