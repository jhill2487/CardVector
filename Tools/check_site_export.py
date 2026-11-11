"""Fail deployment when public web assets or required routes are absent from export."""
from __future__ import annotations
import json
import sys
from pathlib import Path

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "public-site")
    source = Path(sys.argv[2] if len(sys.argv) > 2 else "Docs")
    manifest = root / "deployment-manifest.json"
    required = ("index.html", "404.html", "app.js", "style.css", "account/index.html",
                "account/app.js",
    "wanted/index.html",
    "wanted/style.css",
    "wanted/search.js", "my-wants/index.html", "my-wants/app.js", "dashboard/index.html", "dashboard/app.js", "dashboard/style.css", "settings/index.html", "settings/app.js", "settings/style.css", "status/index.html", "account/style.css", "partners.css", "brand-site.css", "brand-refresh.css", "market-theme.css", "ui-polish.css", "assets/favicon.svg", "partners/index.html", "assets/cardvector-twin-arrow.svg")
    missing = [p for p in required if not (root / p).is_file()]
    if not manifest.is_file():
        missing.append("deployment-manifest.json")
    if missing:
        raise SystemExit("Public site missing required files: " + ", ".join(missing))
    index = (root / "index.html").read_text(encoding="utf-8")
    account = (root / "account/index.html").read_text(encoding="utf-8")
    for needle in ('href="/account/"', 'CardVector', 'href="/partners/"', 'href="/brand-site.css', 'href="/brand-refresh.css', '/assets/cardvector-twin-arrow.svg'):
        if needle not in index:
            raise SystemExit("Public homepage missing: " + needle)
    if not (root / "partners/index.html").is_file():
        raise SystemExit("Public partner page is missing")
    # The buyer-demand marketplace must ship with its data loader, styles and
    # a discoverable homepage link. This guards against partial deployments.
    for relative in ("marketplace/index.html", "marketplace/app.js", "marketplace/style.css"):
        if not (root / relative).is_file():
            raise SystemExit(f"Marketplace export missing: {relative}")
    market_page = (root / "marketplace/index.html").read_text(encoding="utf-8")
    market_script = (root / "marketplace/app.js").read_text(encoding="utf-8")
    if 'href="/marketplace/"' not in index:
        raise SystemExit("Homepage does not link to the live marketplace")
    if not all(fragment in market_page for fragment in ('id="market-results"', 'id="total-requests"', 'id="total-copies"', 'id="total-cards"', '/marketplace/app.js')):
        raise SystemExit("Marketplace page missing required demand/analytics elements")
    if not all(fragment in market_script for fragment in ('cv_public_wants', 'max_price_usd', 'card_id', 'accepted_finishes')):
        raise SystemExit("Marketplace app missing public-demand data contract")

    if '/account/app.js' not in account:
        raise SystemExit("Public account page missing auth script")
    for relative in ("index.html", "account/index.html"):
        if "{{" in (root / relative).read_text(encoding="utf-8"):
            raise SystemExit(f"Unrendered placeholder in {relative}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not data.get("source_commit"):
        raise SystemExit("Deployment manifest lacks source commit")

    # Every local static HTML reference must carry the current release version.
    import re
    expected_version = data["source_commit"][:12]
    for page in root.rglob("*.html"):
        content = page.read_text(encoding="utf-8")
        for match in re.finditer(r"""\b(?:src|href)=["'](/[^"'?#]+\.(?:css|js|svg|png|jpe?g|webp|gif|ico)(?:\?[^"']*)?)["']""", content, flags=re.I):
            url = match.group(1)
            if f"cv={expected_version}" not in url:
                raise SystemExit(f"Unversioned asset in {page.relative_to(root)}: {url}")
    # Any new top-level static file or route in the public source should be
    # explicitly included in the exporter, rather than silently ignored.
    ignored = {"site-config.json", "README.md", "PROJECT_MANUAL.md", "CHANGELOG.md",
               "CNAME", "_config.yml", "robots.txt", "app.js", "style.css",
               "index.html", "404.html", "partners.css", "brand-site.css", "brand-refresh.css"}
    for p in source.iterdir():
        if p.is_file() and p.suffix.lower() in {".html", ".css", ".js"} and p.name not in ignored:
            if not (root / p.name).is_file():
                raise SystemExit(f"New top-level public asset omitted from export: {p.name}")
    # Prevent silently dropping new HTML pages from the public export.
    for page in source.rglob("index.html"):
        relative = page.relative_to(source)
        # Diagnostic tools are not part of the public website export. Do not
        # force their publication merely to satisfy export completeness.
        if relative.parts[:2] == ("tools", "variant-diagnostic"):
            continue
        if any(part in {"Reference", "Reports", "Archive", "content"} for part in relative.parts):
            continue
        if not (root / relative).is_file():
            raise SystemExit(f"Authored public page omitted from export: {relative}")
    print("Public site export verified (collector account, marketplace demand, partners, and manifest).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
