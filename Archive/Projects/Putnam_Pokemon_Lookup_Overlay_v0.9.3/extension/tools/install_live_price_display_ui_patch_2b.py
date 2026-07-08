
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re


def find_extension_root() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here,
        here.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]
    for candidate in candidates:
        if (candidate / "overlay.js").exists() and (candidate / "overlay.css").exists():
            return candidate
    print("ERROR: Could not find extension folder containing overlay.js and overlay.css.")
    print("Save this installer in:")
    print(r"C:\Users\JaredHill\OneDrive\PutnamCollectibles\Pokemon_Live_Price_Lookup\extension\tools")
    raise SystemExit(1)


EXTENSION = find_extension_root()
ARCHIVE = EXTENSION / "archive_old_versions"
OVERLAY_JS = EXTENSION / "overlay.js"
OVERLAY_CSS = EXTENSION / "overlay.css"

ARCHIVE.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

js_src = OVERLAY_JS.read_text(encoding="utf-8")
css_src = OVERLAY_CSS.read_text(encoding="utf-8")

(ARCHIVE / f"overlay_before_live_price_display_2b_patch_{stamp}.js").write_text(js_src, encoding="utf-8")
(ARCHIVE / f"overlay_before_live_price_display_2b_patch_{stamp}.css").write_text(css_src, encoding="utf-8")


new_render_func = r'''  function priceObject(variant, condition) {
    return variant?.conditions?.[condition] || null;
  }

  function priceValue(item) {
    return item?.market ?? item?.market_price ?? item?.low ?? item?.price ?? null;
  }

  function priceText(item) {
    const value = priceValue(item);
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value);
    return `$${number.toFixed(2)}`;
  }

  function formatFinish(value) {
    const raw = String(value || "Normal").trim();
    if (!raw || raw.toLowerCase() === "normal") return "Normal";
    return raw
      .replace(/reverse holofoil/i, "Reverse Holo")
      .replace(/holofoil/i, "Holo");
  }

  function formatUpdated(value) {
    if (!value) return "";
    const date = new Date(String(value).replace(" ", "T"));
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function firstRankedVariant(prices) {
    const variants = Array.isArray(prices?.variants) ? [...prices.variants] : [];
    variants.sort((a, b) => {
      const ar = Number(a?.variant_match_rank || 0);
      const br = Number(b?.variant_match_rank || 0);
      return br - ar;
    });
    return variants[0] || null;
  }

  function productLink(variant, card) {
    return variant?.tcgplayer_url || variant?.product_url || card?.tcgplayer_search_url || card?.tcgplayer_url || "";
  }

  function renderVariantPrices(card, prices) {
    const variant = firstRankedVariant(prices);

    if (!variant) {
      const nm = pickPrice(prices, ["NM", "Near Mint"]);
      const lp = pickPrice(prices, ["LP", "Lightly Played"]);
      const market = pickPrice(prices, ["MARKET", "market", "raw"]);
      const text = nm || lp
        ? `NM ${nm || "—"} · LP ${lp || "—"}`
        : market
          ? `Market ${market}`
          : "No price found";
      return el("div", {
        className: `ppo-price-badge ${nm || lp || market ? "" : "ppo-muted-price"}`,
        text,
      });
    }

    const wrap = el("div", { className: "ppo-live-price-card" });

    const titleText = `${variant.product_name || card.card_name || "Card"} - ${variant.set_name || card.set_name || ""} ${variant.card_number || card.printed_number || ""}`.trim();
    wrap.append(el("div", { className: "ppo-live-title", text: titleText }));

    const rank = variant.variant_match_rank;
    if (rank !== undefined && rank !== null) {
      wrap.append(el("div", { className: "ppo-live-subtitle", text: `Primary match · score ${rank}` }));
    }

    const table = el("div", { className: "ppo-live-price-table" });
    table.append(el("div", { className: "ppo-live-cell ppo-live-head", text: "Finish" }));
    table.append(el("div", { className: "ppo-live-cell ppo-live-head", text: "NM" }));
    table.append(el("div", { className: "ppo-live-cell ppo-live-head", text: "LP" }));

    const nm = priceObject(variant, "NM");
    const lp = priceObject(variant, "LP");
    const url = productLink(variant, card);

    table.append(el("div", { className: "ppo-live-cell ppo-live-finish", text: formatFinish(variant.finish) }));

    const nmCell = el("div", { className: `ppo-live-cell ppo-live-price ${nm?.source === "tcgplayer_live" ? "ppo-live-source" : "ppo-cache-source"}` });
    const lpCell = el("div", { className: `ppo-live-cell ppo-live-price ${lp?.source === "tcgplayer_live" ? "ppo-live-source" : "ppo-cache-source"}` });

    if (url && priceText(nm) !== "—") {
      nmCell.append(el("a", { text: priceText(nm), attrs: { href: url, target: "_blank", rel: "noopener noreferrer" } }));
    } else {
      nmCell.textContent = priceText(nm);
    }

    if (url && priceText(lp) !== "—") {
      lpCell.append(el("a", { text: priceText(lp), attrs: { href: url, target: "_blank", rel: "noopener noreferrer" } }));
    } else {
      lpCell.textContent = priceText(lp);
    }

    table.append(nmCell);
    table.append(lpCell);
    wrap.append(table);

    const liveUpdated = variant.live_fetched_at || nm?.fetched_at || lp?.fetched_at || "";
    const liveLine = variant.live_price_source === "tcgplayer_live"
      ? `Live TCGplayer · updated ${formatUpdated(liveUpdated) || liveUpdated || "now"}`
      : `Cached price${liveUpdated ? ` · updated ${formatUpdated(liveUpdated)}` : ""}`;

    wrap.append(el("div", { className: "ppo-live-meta", text: liveLine }));

    if (url) {
      wrap.append(el("a", {
        className: "ppo-live-link",
        text: "View Listings",
        attrs: { href: url, target: "_blank", rel: "noopener noreferrer" },
      }));
    }

    const alternates = Array.isArray(prices?.variants) ? prices.variants.length - 1 : 0;
    if (alternates > 0) {
      wrap.append(el("div", { className: "ppo-live-alternates", text: `${alternates} alternate variant${alternates === 1 ? "" : "s"} hidden` }));
    }

    return wrap;
  }
'''

pattern = re.compile(
    r"  function renderVariantPrices\(card, prices\) \{.*?\n  \}\n\n  function createOverlay\(",
    re.S,
)

if not pattern.search(js_src):
    print("ERROR: Could not find renderVariantPrices() block in overlay.js. No changes written.")
    raise SystemExit(1)

js_src = pattern.sub(new_render_func + "\n\n  const root = el(\"div\", { id: \"putnam-pokemon-overlay\" });", js_src)
js_src = js_src.replace('const title = el("strong", { text: "Pokemon Lookup" });', 'const title = el("strong", { text: "Putnam Price Lookup" });')
OVERLAY_JS.write_text(js_src, encoding="utf-8")


css_add = r'''

/* Patch 2B - Live Price Display UI */
.ppo-live-price-card {
  margin-top: 8px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  padding: 9px;
  background: rgba(15, 23, 42, 0.55);
}

.ppo-live-title {
  font-weight: 700;
  font-size: 12px;
  line-height: 1.25;
  margin-bottom: 2px;
}

.ppo-live-subtitle {
  font-size: 10px;
  color: #94a3b8;
  margin-bottom: 7px;
}

.ppo-live-price-table {
  display: grid;
  grid-template-columns: minmax(88px, 1.2fr) minmax(58px, 0.8fr) minmax(58px, 0.8fr);
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 8px;
  overflow: hidden;
  margin-top: 6px;
}

.ppo-live-cell {
  padding: 6px 7px;
  border-right: 1px solid rgba(148, 163, 184, 0.22);
  border-bottom: 1px solid rgba(148, 163, 184, 0.22);
  font-size: 11px;
}

.ppo-live-cell:nth-child(3n) {
  border-right: none;
}

.ppo-live-cell:nth-last-child(-n + 3) {
  border-bottom: none;
}

.ppo-live-head {
  font-weight: 700;
  color: #cbd5e1;
  background: rgba(30, 41, 59, 0.75);
}

.ppo-live-finish {
  color: #e5e7eb;
  font-weight: 600;
}

.ppo-live-price {
  text-align: right;
  font-weight: 800;
}

.ppo-live-price a {
  color: inherit;
  text-decoration: none;
}

.ppo-live-price a:hover {
  text-decoration: underline;
}

.ppo-live-source {
  color: #86efac;
}

.ppo-cache-source {
  color: #fde68a;
}

.ppo-live-meta {
  margin-top: 6px;
  font-size: 10px;
  color: #94a3b8;
}

.ppo-live-link {
  display: inline-flex;
  margin-top: 7px;
  padding: 5px 8px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.95);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  text-decoration: none;
}

.ppo-live-link:hover {
  background: rgba(59, 130, 246, 1);
}

.ppo-live-alternates {
  margin-top: 6px;
  font-size: 10px;
  color: #64748b;
}
'''

if "Patch 2B - Live Price Display UI" not in css_src:
    css_src = css_src.rstrip() + css_add + "\n"

OVERLAY_CSS.write_text(css_src, encoding="utf-8")

print("Patch 2B installed successfully.")
print("Patch name: Patch_2B_Live_Price_Display_UI")
print("Extension:", EXTENSION)
print("Patched:", OVERLAY_JS)
print("Patched:", OVERLAY_CSS)
print("Backup folder:", ARCHIVE)
print("")
print("Next steps:")
print("1. Reload the Chrome extension at chrome://extensions")
print("2. Restart backend if needed")
print("3. Search pikachu / base in the overlay")
print("Expected: Putnam Price Lookup title and compact Finish | NM | LP live price table.")

