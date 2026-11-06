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
                "account/app.js", "account/style.css", "partners.css", "brand-site.css", "partners/index.html")
    missing = [p for p in required if not (root / p).is_file()]
    if not manifest.is_file():
        missing.append("deployment-manifest.json")
    if missing:
        raise SystemExit("Public site missing required files: " + ", ".join(missing))
    index = (root / "index.html").read_text(encoding="utf-8")
    account = (root / "account/index.html").read_text(encoding="utf-8")
    for needle in ('href="/account/"', 'CardVector', 'href="/partners/"', 'href="/brand-site.css'):
        if needle not in index:
            raise SystemExit("Public homepage missing: " + needle)
    if not (root / "partners/index.html").is_file():
        raise SystemExit("Public partner page is missing")
    if '/account/app.js' not in account:
        raise SystemExit("Public account page missing auth script")
    for relative in ("index.html", "account/index.html"):
        if "{{" in (root / relative).read_text(encoding="utf-8"):
            raise SystemExit(f"Unrendered placeholder in {relative}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not data.get("source_commit"):
        raise SystemExit("Deployment manifest lacks source commit")
    # Any new top-level static file or route in the public source should be
    # explicitly included in the exporter, rather than silently ignored.
    ignored = {"site-config.json", "README.md", "PROJECT_MANUAL.md", "CHANGELOG.md",
               "CNAME", "_config.yml", "robots.txt", "app.js", "style.css",
               "index.html", "404.html", "partners.css", "brand-site.css"}
    for p in source.iterdir():
        if p.is_file() and p.suffix.lower() in {".html", ".css", ".js"} and p.name not in ignored:
            if not (root / p.name).is_file():
                raise SystemExit(f"New top-level public asset omitted from export: {p.name}")
    # Prevent silently dropping new HTML pages from the public export.
    for page in source.rglob("index.html"):
        relative = page.relative_to(source)
        if any(part in {"Reference", "Reports", "Archive", "content"} for part in relative.parts):
            continue
        if not (root / relative).is_file():
            raise SystemExit(f"Authored public page omitted from export: {relative}")
    print("Public site export verified (collector account, partners, and manifest).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
