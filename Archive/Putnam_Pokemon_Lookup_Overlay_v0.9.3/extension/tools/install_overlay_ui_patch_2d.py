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

(ARCHIVE / f"overlay_before_patch_2d_{stamp}.js").write_text(js, encoding="utf-8")
(ARCHIVE / f"overlay_before_patch_2d_{stamp}.css").write_text(css, encoding="utf-8")

# Remove price source line.
js = js.replace(
    '''      if (prices?.source || card.price_source) {
        details.append(el("span", { className: "ppo-price-source", text: `Price source: ${prices.source || card.price_source}` }));
      }

''',
    ""
)

# Make card details uppercase and move set+number into main detail line.
js = js.replace(
    '''      details.append(
        el("strong", { text: card.card_name || card.name || "Unknown card" }),
        el("span", { text: `${card.set_name || card.set || "Unknown set"} ${card.printed_number || card.card_number || card.number || ""}`.trim() }),
        el("span", { text: card.rarity ? `Rarity: ${card.rarity}` : "" }),
        el("span", { text: card.confidence ? `Database match: ${Math.round(Number(card.confidence) * 100)}%` : "" })
      );
''',
    '''      const setLine = `${card.set_name || card.set || "UNKNOWN SET"} ${card.printed_number || card.card_number || card.number || ""}`.trim().toUpperCase();
      details.append(
        el("strong", { text: String(card.card_name || card.name || "UNKNOWN CARD").toUpperCase() }),
        el("span", { className: "ppo-card-setline", text: setLine }),
        el("span", { className: "ppo-card-rarity", text: card.rarity ? `RARITY: ${String(card.rarity).toUpperCase()}` : "" }),
        el("span", { text: card.confidence ? `DATABASE MATCH: ${Math.round(Number(card.confidence) * 100)}%` : "" })
      );
'''
)

# Normalize finish label.
js = js.replace(
    '''    return raw
      .replace(/reverse holofoil/i, "Reverse Holo")
      .replace(/holofoil/i, "Holo");''',
    '''    return raw
      .replace(/reverse holofoil/i, "REVERSE HOLO")
      .replace(/holofoil/i, "HOLO")
      .toUpperCase();'''
)

# Simplify title inside live price card.
js = js.replace(
    '''    const titleText = `${variant.product_name || card.card_name || "Card"} - ${variant.set_name || card.set_name || ""} ${variant.card_number || card.printed_number || ""}`.trim();
    wrap.append(el("div", { className: "ppo-live-title", text: titleText }));

    if (variant.variant_match_rank !== undefined && variant.variant_match_rank !== null) {
      wrap.append(el("div", { className: "ppo-live-subtitle", text: `Primary match · score ${variant.variant_match_rank}` }));
    }
''',
    '''    const matchText = variant.variant_match_rank !== undefined && variant.variant_match_rank !== null
      ? `PRIMARY MATCH • SCORE ${variant.variant_match_rank}`
      : "PRIMARY MATCH";
    wrap.append(el("div", { className: "ppo-live-subtitle", text: matchText }));
'''
)

# Uppercase headers.
js = js.replace('text: "Finish"', 'text: "FINISH"')
js = js.replace('text: "NM"', 'text: "NM (NEAR MINT)"')
js = js.replace('text: "LP"', 'text: "LP (LIGHTLY PLAYED)"')

# Uppercase footer/link.
js = js.replace('`Live TCGplayer · updated ${formatUpdated(liveUpdated) || liveUpdated || "now"}`', '`LIVE TCGPLAYER • UPDATED ${formatUpdated(liveUpdated) || liveUpdated || "NOW"}`')
js = js.replace('`Cached price${liveUpdated ? ` · updated ${formatUpdated(liveUpdated)}` : ""}`', '`CACHED PRICE${liveUpdated ? ` • UPDATED ${formatUpdated(liveUpdated)}` : ""}`')
js = js.replace('text: "View Listings"', 'text: "VIEW LISTINGS"')

# Remove alternate variants hidden line.
js = js.replace(
    '''    const alternates = Array.isArray(prices?.variants) ? prices.variants.length - 1 : 0;
    if (alternates > 0) {
      wrap.append(el("div", { className: "ppo-live-alternates", text: `${alternates} alternate variant${alternates === 1 ? "" : "s"} hidden` }));
    }

''',
    ""
)

CSS.write_text(css + r'''

/* Patch 2D - Overlay UI Modernization */
.ppo-result {
  background: #ffffff !important;
  color: #111827 !important;
  border: 1px solid #d1d5db !important;
}

.ppo-result-details strong {
  color: #050505 !important;
  font-weight: 900 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
}

.ppo-result-details span {
  color: #111827 !important;
  font-weight: 700 !important;
  letter-spacing: 0.035em !important;
}

.ppo-card-setline,
.ppo-card-rarity {
  text-transform: uppercase !important;
}

.ppo-live-price-card {
  margin-top: 10px !important;
  background: #ffffff !important;
  color: #111827 !important;
  border: 1px solid #9ca3af !important;
  border-radius: 8px !important;
  padding: 0 !important;
  overflow: hidden !important;
  box-shadow: none !important;
}

.ppo-live-subtitle {
  padding: 10px 12px 6px 12px !important;
  color: #111827 !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
}

.ppo-live-price-table {
  display: grid !important;
  grid-template-columns: 1fr 1.25fr 1.25fr !important;
  margin: 6px 10px 0 10px !important;
  border: 1px solid #d1d5db !important;
  border-radius: 7px !important;
  overflow: hidden !important;
  background: #ffffff !important;
}

.ppo-live-cell {
  padding: 8px 7px !important;
  border-right: 1px solid #d1d5db !important;
  border-bottom: 1px solid #d1d5db !important;
  font-size: 11px !important;
  color: #111827 !important;
  background: #ffffff !important;
  text-align: center !important;
}

.ppo-live-head {
  color: #050505 !important;
  background: #ffffff !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}

.ppo-live-finish {
  color: #050505 !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}

.ppo-live-price {
  color: #08751f !important;
  font-size: 14px !important;
  font-weight: 900 !important;
  letter-spacing: 0.04em !important;
}

.ppo-live-price a {
  color: #08751f !important;
  text-decoration: none !important;
}

.ppo-live-meta {
  margin: 0 !important;
  padding: 9px 10px !important;
  color: #111827 !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  letter-spacing: 0.045em !important;
  text-transform: uppercase !important;
  border-top: 1px solid #d1d5db !important;
  display: inline-block !important;
}

.ppo-live-link {
  float: right !important;
  margin: 7px 10px 8px 0 !important;
  padding: 8px 12px !important;
  border-radius: 7px !important;
  background: #165df5 !important;
  color: #ffffff !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  letter-spacing: 0.05em !important;
  text-transform: uppercase !important;
  text-decoration: none !important;
}

.ppo-live-link:hover {
  background: #004ce8 !important;
}

.ppo-price-source,
.ppo-live-title,
.ppo-live-alternates {
  display: none !important;
}
''', encoding="utf-8")

JS.write_text(js, encoding="utf-8")

print("Patch 2D installed: modern white price card UI, uppercase labels, no price source line.")
print("Backups saved to:", ARCHIVE)