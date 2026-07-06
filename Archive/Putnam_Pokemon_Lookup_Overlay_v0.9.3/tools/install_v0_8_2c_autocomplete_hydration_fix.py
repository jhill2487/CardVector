from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "extension" / "overlay.js"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_8_2c_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

marker = '''  function priceText(item) {
    const value = priceValue(item);
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value);
    return `$${number.toFixed(2)}`;
  }

'''

insert = '''  function priceText(item) {
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

'''

if marker not in js:
    raise SystemExit("ERROR: Could not find priceText marker. No changes written.")

js = js.replace(marker, insert, 1)

old = '''      if (prices && Object.keys(prices).length) {
        priceMount.append(renderVariantPrices(card, prices));
      } else if (shouldLoadInitial && card.putnam_card_id) {'''

new = '''      if (hasUsablePrices(prices)) {
        priceMount.append(renderVariantPrices(card, prices));
      } else if (shouldLoadInitial && card.putnam_card_id) {'''

if old not in js:
    raise SystemExit("ERROR: Could not find renderResults price hydration condition. No changes written.")

js = js.replace(old, new, 1)

JS.write_text(js, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.8.2.3"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.8.2C Autocomplete Hydration Fix")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")