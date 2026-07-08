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

(ARCHIVE / f"overlay_before_patch_2d_1_{stamp}.js").write_text(js, encoding="utf-8")
(ARCHIVE / f"overlay_before_patch_2d_1_{stamp}.css").write_text(css, encoding="utf-8")

# Remove primary match score display.
js = js.replace(
'''    const matchText = variant.variant_match_rank !== undefined && variant.variant_match_rank !== null
      ? `PRIMARY MATCH • SCORE ${variant.variant_match_rank}`
      : "PRIMARY MATCH";
    wrap.append(el("div", { className: "ppo-live-subtitle", text: matchText }));
''',
""
)

# Fallback removal if block has slightly different text.
js = js.replace(
'''    wrap.append(el("div", { className: "ppo-live-subtitle", text: matchText }));
''',
""
)

# Simplify condition headers.
js = js.replace('text: "NM (NEAR MINT)"', 'text: "NM"')
js = js.replace('text: "LP (LIGHTLY PLAYED)"', 'text: "LP"')

# Upgrade the set/card number line for Scarlet & Violet 151.
js = js.replace(
'''      const setLine = `${card.set_name || card.set || "UNKNOWN SET"} ${card.printed_number || card.card_number || card.number || ""}`.trim().toUpperCase();
''',
'''      function displaySetName(card) {
        const raw = String(card.set_name || card.set || "UNKNOWN SET").trim();
        if (raw.toLowerCase() === "151") return "SV: SCARLET & VIOLET 151";
        return raw.toUpperCase();
      }

      const setLine = `${displaySetName(card)} ${card.printed_number || card.card_number || card.number || ""}`.trim().toUpperCase();
'''
)

# Remove any leftover subtitle visual spacing.
css += r'''

/* Patch 2D.1 - Production UI Cleanup */
.ppo-live-subtitle {
  display: none !important;
}

.ppo-live-price-card {
  padding-top: 0 !important;
}

.ppo-live-price-table {
  margin-top: 10px !important;
}

.ppo-live-head {
  font-size: 11px !important;
  line-height: 1.1 !important;
}

.ppo-card-setline {
  font-weight: 900 !important;
}
'''

JS.write_text(js, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")

print("Patch 2D.1 installed.")
print("Removed primary match score display.")
print("Simplified NM / LP headers.")
print("Updated 151 set display to SV: SCARLET & VIOLET 151.")
print("Backups saved to:", ARCHIVE)