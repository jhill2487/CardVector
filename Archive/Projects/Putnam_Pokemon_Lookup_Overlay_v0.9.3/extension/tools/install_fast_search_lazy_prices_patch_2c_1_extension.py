from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
JS = ROOT / "overlay.js"
CSS = ROOT / "overlay.css"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
js = JS.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

(ARCHIVE / f"overlay_before_patch_2c_1_{stamp}.js").write_text(js, encoding="utf-8")
(ARCHIVE / f"overlay_before_patch_2c_1_{stamp}.css").write_text(css, encoding="utf-8")

if "async function loadLazyPrices" not in js:
    js = js.replace(
        "  function renderResults(results) {\n",
        '''  async function loadLazyPrices(card, mount) {
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
    mount.replaceChildren(renderVariantPrices(card, card.prices || {}));
  }

  function renderResults(results) {
'''
    )

old = '''      details.append(renderVariantPrices(card, prices));

      row.append(media, details);
'''

new = '''      const priceMount = el("div", { className: "ppo-price-mount" });
      const isFirstResult = results.indexOf(card) === 0;

      if (prices && Object.keys(prices).length) {
        priceMount.append(renderVariantPrices(card, prices));
      } else if (isFirstResult && card.putnam_card_id) {
        priceMount.append(el("div", {
          className: "ppo-price-loading",
          text: "LOADING LIVE PRICE..."
        }));
        setTimeout(() => {
          loadLazyPrices(card, priceMount).catch((error) => {
            priceMount.replaceChildren(el("div", {
              className: "ppo-price-loading ppo-price-error",
              text: error.message || "PRICE LOOKUP FAILED"
            }));
          });
        }, 0);
      } else {
        priceMount.append(renderVariantPrices(card, prices));
      }

      details.append(priceMount);

      row.append(media, details);
'''

if old not in js:
    raise SystemExit("ERROR: Could not find price render insertion point in overlay.js. No changes written.")

js = js.replace(old, new)

if "Patch 2C.1 - Lazy Price Loading UI" not in css:
    css += r'''

/* Patch 2C.1 - Lazy Price Loading UI */
.ppo-price-loading {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #111827;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ppo-price-error {
  color: #b91c1c;
}
'''

JS.write_text(js, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")

print("Patch 2C.1 extension installed.")
print("Search renders immediately; top result lazy-loads live price afterward.")
print("Backup saved to:", ARCHIVE)