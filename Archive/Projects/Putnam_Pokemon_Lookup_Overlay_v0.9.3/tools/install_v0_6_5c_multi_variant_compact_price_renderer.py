from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
OVERLAY_JS = ROOT / "extension" / "overlay.js"
OVERLAY_CSS = ROOT / "extension" / "overlay.css"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [OVERLAY_JS, OVERLAY_CSS]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_5c_{stamp}{p.suffix}")

js = OVERLAY_JS.read_text(encoding="utf-8")

start = js.find("  function renderVariantPrices(card, prices) {")
end = js.find("  const root = el(", start)

if start == -1 or end == -1 or end <= start:
    raise SystemExit("ERROR: Could not locate renderVariantPrices block. No changes written.")

new_block = r'''  function compactVariantLabel(variant) {
    const name = String(variant?.product_name || "").toLowerCase();
    const finish = String(variant?.finish || "").toLowerCase();

    if (name.includes("1st edition") || name.includes("first edition")) return "1st Edition";
    if (name.includes("shadowless")) return "Shadowless";
    if (name.includes("unlimited")) return "Unlimited";

    if (!finish || finish === "normal") return "Normal";
    if (finish.includes("reverse")) return "Reverse";
    if (finish.includes("holo")) return "Holo";
    if (finish.includes("cosmos")) return "Cosmos";
    return formatFinish(finish);
  }

  function samePrintedNumber(card, variant) {
    const clean = (value) => String(value || "").toLowerCase().replace(/[^a-z0-9/]/g, "").replace(/^0+/, "");
    const cardPrinted = clean(card?.printed_number || card?.card_number);
    const variantPrinted = clean(variant?.card_number || variant?.clean_number);

    if (!cardPrinted || !variantPrinted) return true;
    if (cardPrinted === variantPrinted) return true;

    const cardHead = cardPrinted.split("/")[0].replace(/^0+/, "");
    const variantHead = variantPrinted.split("/")[0].replace(/^0+/, "");
    return Boolean(cardHead && variantHead && cardHead === variantHead && !variantPrinted.includes("/"));
  }

  function renderCompactConditionCell(variant, condition, url) {
    const obj = priceObject(variant, condition);
    const text = `${condition} ${priceText(obj)}`;
    const cell = el("span", {
      className: `ppo-compact-price-cell ${obj?.source === "tcgplayer_live" ? "ppo-live-source" : "ppo-cache-source"}`
    });

    if (url && priceText(obj) !== "—") {
      cell.append(el("a", { text, attrs: { href: url, target: "_blank", rel: "noopener noreferrer" } }));
    } else {
      cell.textContent = text;
    }

    return cell;
  }

  function renderVariantPrices(card, prices) {
    const variants = Array.isArray(prices?.variants) ? [...prices.variants] : [];

    if (!variants.length) {
      const nm = pickPrice(prices, ["NM", "near_mint", "Near Mint"]);
      const lp = pickPrice(prices, ["LP", "lightly_played", "Lightly Played"]);
      const mp = pickPrice(prices, ["MP", "moderately_played", "Moderately Played"]);
      const market = pickPrice(prices, ["MARKET", "market", "raw"]);
      const priceTextValue = nm || lp || mp
        ? `${nm ? `NM ${nm}` : ""}${nm && lp ? " " : ""}${lp ? `LP ${lp}` : ""}${(nm || lp) && mp ? " " : ""}${mp ? `MP ${mp}` : ""}`.trim()
        : market
          ? `Market ${market}`
          : "No live price";

      return el("div", {
        className: `ppo-price-badge ${nm || lp || mp || market ? "" : "ppo-muted-price"}`,
        text: priceTextValue
      });
    }

    variants.sort((a, b) => Number(b?.variant_match_rank || 0) - Number(a?.variant_match_rank || 0));

    const wrap = el("div", { className: "ppo-live-price-card ppo-compact-price-card" });
    wrap.append(el("div", { className: "ppo-compact-price-title", text: "PRICE" }));

    const seenLabels = new Set();
    const rows = [];

    for (const variant of variants) {
      if (!samePrintedNumber(card, variant)) continue;

      const label = compactVariantLabel(variant);
      if (seenLabels.has(label)) continue;

      const nm = priceObject(variant, "NM");
      const lp = priceObject(variant, "LP");
      const mp = priceObject(variant, "MP");

      if (priceText(nm) === "—" && priceText(lp) === "—" && priceText(mp) === "—") continue;

      seenLabels.add(label);
      rows.push(variant);

      if (rows.length >= 5) break;
    }

    if (!rows.length && variants[0]) rows.push(variants[0]);

    for (const variant of rows) {
      const url = productLink(variant, card);
      const row = el("div", { className: "ppo-compact-price-row" });
      row.append(el("span", { className: "ppo-compact-variant-label", text: compactVariantLabel(variant) }));
      row.append(renderCompactConditionCell(variant, "NM", url));
      row.append(renderCompactConditionCell(variant, "LP", url));
      row.append(renderCompactConditionCell(variant, "MP", url));
      wrap.append(row);
    }

    const first = rows[0] || variants[0];
    const liveUpdated = first?.live_fetched_at || priceObject(first, "NM")?.fetched_at || priceObject(first, "LP")?.fetched_at || "";
    const liveLine = first?.live_price_source === "tcgplayer_live"
      ? `LIVE TCGPLAYER • UPDATED ${formatUpdated(liveUpdated) || liveUpdated || "NOW"}`
      : `CACHED PRICE${liveUpdated ? ` • UPDATED ${formatUpdated(liveUpdated)}` : ""}`;
    wrap.append(el("div", { className: "ppo-live-meta", text: liveLine }));

    return wrap;
  }

'''

js = js[:start] + new_block + js[end:]
OVERLAY_JS.write_text(js, encoding="utf-8")

css = OVERLAY_CSS.read_text(encoding="utf-8")
if "v0.6.5C multi-variant compact price renderer" not in css:
    css += r'''

/* v0.6.5C multi-variant compact price renderer */
.ppo-compact-price-card {
  padding: 7px 8px;
}

.ppo-compact-price-title {
  font-size: 11px;
  font-weight: 700;
  opacity: 0.85;
  margin-bottom: 4px;
}

.ppo-compact-price-row {
  display: grid;
  grid-template-columns: minmax(62px, 1fr) repeat(3, minmax(58px, 0.9fr));
  gap: 5px;
  align-items: center;
  font-size: 11px;
  line-height: 1.25;
  margin: 2px 0;
}

.ppo-compact-variant-label {
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ppo-compact-price-cell {
  white-space: nowrap;
}

.ppo-compact-price-cell a {
  text-decoration: none;
}
'''

OVERLAY_CSS.write_text(css, encoding="utf-8")

print("Installed v0.6.5C Multi-Variant Compact Price Renderer")
print(f"Backups saved in: {archive}")
print("Files patched:")
print(" - extension/overlay.js")
print(" - extension/overlay.css")