from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PUBLIC_FILES = (
    "index.html",
    "404.html",
    "app.js",
    "style.css",
    "mobile-capture-config.js",
    "robots.txt",
    "tools/carduploader/index.html",
    "CNAME",
    "_config.yml",
)

PUBLIC_ASSETS = (
    "assets/putnam-profile.png",
    "assets/putnam-profile-onepiece.png",
    "assets/putnam-ebay-banner.png",
)

SITE_CONFIG_FILE = "site-config.json"
MARKET_BRIEF_SOURCE_DIR = Path("content") / "market-briefs"
MARKET_BRIEF_INDEX_FILE = MARKET_BRIEF_SOURCE_DIR / "index.json"
SITE_URL = "https://cardvector.app"
SITE_CONFIG_KEYS = (
    "EBAY_STORE_URL",
    "TCGPLAYER_STORE_URL",
    "MANAPOOL_STORE_URL",
    "CARDUPLOADER_REFERRAL_URL",
    "WHATNOT_REFERRAL_URL",
    "WHATNOT_SELLER_REFERRAL_URL",
    "COLLECTION_INQUIRY_URL",
    "CONTACT_EMAIL",
    "CONTACT_EMAIL_URL",
)

PROHIBITED_PARTS = {
    "Reference",
    "Reports",
    "Archive",
    "Business",
    "Data",
    "Platform",
    "Work_Sessions",
    "__pycache__",
}

PROHIBITED_SUFFIXES = {
    ".py",
    ".pyc",
    ".sqlite",
    ".db",
    ".csv",
    ".xlsx",
    ".xls",
    ".docx",
    ".pdf",
    ".log",
    ".tmp",
}

CLIENT_ROUTES = {
    "about",
    "batch-workflow",
    "batches",
    "buylist",
    "bulk",
    "capture",
    "contact",
    "events",
    "etb",
    "location",
    "lot",
    "market",
    "market-briefs",
    "listings",
    "listing-reconciliation",
    "mobile",
    "mobile-capture",
    "operator",
    "price-review",
    "repricing",
    "sell",
    "tools",
    "registry",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_commit(default: str = "") -> str:
    if default:
        return default
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def clean_output(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for item in output.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item, onexc=make_writable_and_retry)
        else:
            make_writable(item)
            item.unlink()


def make_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | 0o200)
    except OSError:
        pass


def make_writable_and_retry(function, path: str, _excinfo) -> None:
    make_writable(Path(path))
    function(path)


def copy_file(source_root: Path, output: Path, relative: str) -> None:
    source = source_root / relative
    if not source.exists():
        raise FileNotFoundError(f"Required public file is missing: {source}")
    destination = output / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def load_site_config(source_root: Path) -> dict[str, str]:
    path = source_root / SITE_CONFIG_FILE
    if not path.exists():
        raise FileNotFoundError(f"Required public site configuration is missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Public site configuration must be a JSON object: {path}")
    config = {}
    for key in SITE_CONFIG_KEYS:
        value = str(data.get(key, "") or "").strip()
        if key == "CONTACT_EMAIL":
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
                raise ValueError(f"{key} must be a complete email address.")
        elif not value.startswith("https://"):
            raise ValueError(f"{key} must be a complete https:// URL.")
        if "PASTE_" in value.upper() or "PLACEHOLDER" in value.upper():
            raise ValueError(f"{key} still contains a placeholder value.")
        config[key] = value
    return config


def render_site_config(output: Path, config: dict[str, str]) -> None:
    token_pattern = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
    for path in output.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".html", ".js", ".xml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        for key, value in config.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        unresolved = sorted(set(token_pattern.findall(text)))
        if unresolved:
            relative = path.relative_to(output)
            raise RuntimeError(f"Unresolved public site configuration in {relative}: {', '.join(unresolved)}")
        path.write_text(text, encoding="utf-8")


def parse_frontmatter_value(value: str) -> object:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def parse_markdown_frontmatter(text: str, path: Path) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        raise ValueError(f"Market brief markdown is missing frontmatter: {path}")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"Market brief markdown frontmatter is not closed: {path}")
    raw_frontmatter = text[4:end].strip().splitlines()
    body = text[end + 4 :].strip()
    metadata: dict[str, object] = {}
    current_list_key = ""
    for raw_line in raw_frontmatter:
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("  - ") and current_list_key:
            values = metadata.setdefault(current_list_key, [])
            if not isinstance(values, list):
                raise ValueError(f"Frontmatter key cannot be both scalar and list: {current_list_key}")
            values.append(str(parse_frontmatter_value(line[4:])))
            continue
        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line in {path}: {line}")
        key, value = line.split(":", 1)
        current_list_key = key.strip()
        if value.strip():
            metadata[current_list_key] = parse_frontmatter_value(value)
            current_list_key = ""
        else:
            metadata[current_list_key] = []
    return metadata, body


def markdown_sections(body: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_heading = "Brief"
    current_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append({"heading": current_heading, "body": "\n".join(current_lines).strip()})
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append({"heading": current_heading, "body": "\n".join(current_lines).strip()})
    return [section for section in sections if section["heading"] and section["body"]]


def escape_html(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def market_brief_url(post: dict[str, object]) -> str:
    return f"{SITE_URL}/market-briefs/{post['slug']}"


def date_label_for_brief(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Monday mornings"
    try:
        parsed = datetime.fromisoformat(raw)
        return f"{parsed:%b} {parsed.day}, {parsed:%Y}"
    except Exception:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
            return f"{parsed:%b} {parsed.day}, {parsed:%Y}"
        except Exception:
            return raw


def render_json_ld(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def render_public_header(title: str, description: str, canonical_url: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-WQEKL0NGJ3"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());

    gtag('config', 'G-WQEKL0NGJ3');
  </script>
  <meta name="description" content="{escape_html(description)}">
  <link rel="canonical" href="{escape_html(canonical_url)}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{escape_html(title)}">
  <meta property="og:description" content="{escape_html(description)}">
  <meta property="og:url" content="{escape_html(canonical_url)}">
  <meta property="og:image" content="{SITE_URL}/assets/putnam-ebay-banner.png">
  <meta name="twitter:card" content="summary_large_image">
  <title>{escape_html(title)}</title>
  <link rel="stylesheet" href="/style.css?v=20260812-seo">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header" aria-label="Primary">
    <nav class="nav wrap">
      <a class="brand" href="/" aria-label="Putnam Collectibles home">
        <img class="brand-logo" src="/assets/putnam-profile-onepiece.png" alt="" width="42" height="42">
        <span class="brand-text">Putnam Collectibles</span>
      </a>
      <details class="nav-menu" open>
        <summary aria-label="Open site navigation">Menu</summary>
        <ul class="nav-links" aria-label="Site navigation">
          <li><a class="nav-shop nav-cta" href="{{EBAY_STORE_URL}}" target="_blank" rel="noopener noreferrer">Shop eBay</a></li>
          <li><a class="nav-shop nav-cta-secondary" href="{{TCGPLAYER_STORE_URL}}" target="_blank" rel="noopener noreferrer">Shop TCGplayer</a></li>
          <li><a class="nav-shop nav-cta-secondary" href="{{MANAPOOL_STORE_URL}}" target="_blank" rel="noopener noreferrer">Shop Manapool</a></li>
          <li><a href="/market-briefs">Market Briefs</a></li>
          <li><a href="/sell">Sell Your Collection</a></li>
          <li><a href="/tools/carduploader">CardUploader</a></li>
          <li><a href="/#contact">Contact</a></li>
        </ul>
      </details>
    </nav>
  </header>
  <main id="main">"""


def render_public_footer() -> str:
    return """  </main>
  <footer class="footer">
    <div class="wrap footer-inner">
      <p>&copy; 2026 Putnam Collectibles</p>
      <ul>
        <li><a href="/market-briefs">Market Briefs</a></li>
        <li><a href="/tools/carduploader">CardUploader</a></li>
        <li><a href="{{EBAY_STORE_URL}}" target="_blank" rel="noopener noreferrer">Shop eBay</a></li>
        <li><a href="{{TCGPLAYER_STORE_URL}}" target="_blank" rel="noopener noreferrer">Shop TCGplayer</a></li>
        <li><a href="{{MANAPOOL_STORE_URL}}" target="_blank" rel="noopener noreferrer">Shop Manapool</a></li>
      </ul>
    </div>
  </footer>
  <script src="/app.js?v=20260812-seo" defer></script>
</body>
</html>
"""


def render_brief_section(section: dict[str, str]) -> str:
    paragraphs = [
        f"<p>{escape_html(paragraph.strip())}</p>"
        for paragraph in re.split(r"\n{2,}", section["body"])
        if paragraph.strip()
    ]
    return f"""
          <section class="brief-post-section">
            <h2>{escape_html(section["heading"])}</h2>
            {''.join(paragraphs)}
          </section>"""


def render_market_brief_static_pages(output: Path, posts: list[dict[str, object]]) -> None:
    brief_dir = output / "market-briefs"
    brief_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for post in posts:
        url = f"/market-briefs/{escape_html(post['slug'])}"
        cards.append(f"""
        <article class="brief-card">
          <span class="brief-kicker">{escape_html(post.get("label", "Market Brief"))}</span>
          <h2>{escape_html(post["title"])}</h2>
          <p>{escape_html(post["summary"])}</p>
          <div class="brief-card-footer">
            <span>{escape_html(date_label_for_brief(post.get("date", "")))}</span>
            <a class="button secondary" href="{url}">Open Brief</a>
          </div>
        </article>""")
    index_html = render_public_header(
        "Pokemon Market Briefs | Putnam Collectibles",
        "Weekly Pokemon card market updates, seller strategy, and trading card inventory notes from Putnam Collectibles.",
        f"{SITE_URL}/market-briefs",
    ) + f"""
    <section class="blog-shell wrap" aria-labelledby="market-briefs-page-title">
      <div class="blog-hero">
        <p class="eyebrow">Pokemon market updates</p>
        <h1 id="market-briefs-page-title">Pokemon Market Briefs</h1>
        <p>Weekly Monday morning notes on Pokemon market movement, collector demand, seller strategy, and marketplace signals.</p>
      </div>
      <div class="brief-grid">
        {''.join(cards)}
      </div>
    </section>
""" + render_public_footer()
    (brief_dir / "index.html").write_text(index_html, encoding="utf-8")

    for post in posts:
        slug_dir = brief_dir / str(post["slug"])
        slug_dir.mkdir(parents=True, exist_ok=True)
        post_url = market_brief_url(post)
        sections = "".join(render_brief_section(section) for section in post.get("sections", []))
        json_ld = render_json_ld({
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post["title"],
            "description": post["summary"],
            "datePublished": post.get("date", ""),
            "dateModified": post.get("date", ""),
            "author": {"@type": "Organization", "name": "Putnam Collectibles"},
            "publisher": {
                "@type": "Organization",
                "name": "Putnam Collectibles",
                "url": SITE_URL,
                "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/putnam-profile-onepiece.png"}
            },
            "mainEntityOfPage": {"@type": "WebPage", "@id": post_url},
        })
        post_html = render_public_header(
            f"{post['title']} | Putnam Collectibles",
            str(post["summary"]),
            post_url,
        ) + f"""
    <script type="application/ld+json">{json_ld}</script>
    <article class="blog-shell blog-post wrap" aria-labelledby="market-brief-post-title">
      <a class="operator-inline-link" href="/market-briefs">Back to Market Briefs</a>
      <p class="eyebrow">{escape_html(post.get("label", "Market Brief"))}</p>
      <h1 id="market-brief-post-title">{escape_html(post["title"])}</h1>
      <p class="blog-meta">{escape_html(date_label_for_brief(post.get("date", "")))} &middot; {escape_html(post.get("status", "published"))}</p>
      <p class="hero-lede">{escape_html(post["summary"])}</p>
      <div class="brief-post-layout">{sections}</div>
      <aside class="brief-disclosure">
        <strong>Editorial note</strong>
        <p>Market briefs are informational commentary, not financial advice. Verify current marketplace data before buying, selling, or repricing.</p>
      </aside>
    </article>
""" + render_public_footer()
        (slug_dir / "index.html").write_text(post_html, encoding="utf-8")


def render_sitemap(output: Path, posts: list[dict[str, object]]) -> None:
    urls = [
        (SITE_URL + "/", "2026-08-12", "weekly", "1.0"),
        (SITE_URL + "/market-briefs", "2026-08-12", "weekly", "0.8"),
        (SITE_URL + "/tools/carduploader", "2026-08-12", "monthly", "0.8"),
    ]
    for post in posts:
        urls.append((market_brief_url(post), str(post.get("date", "2026-08-12") or "2026-08-12"), "monthly", "0.7"))
    entries = "\n".join(
        f"  <url><loc>{escape_html(loc)}</loc><lastmod>{escape_html(lastmod)}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>"
        for loc, lastmod, freq, priority in urls
    )
    (output / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n',
        encoding="utf-8",
    )


def parse_affiliate_links(value: object, path: Path) -> list[dict[str, str]]:
    if not value:
        return []
    raw_values = value if isinstance(value, list) else [value]
    links: list[dict[str, str]] = []
    for raw_value in raw_values:
        text = str(raw_value or "").strip()
        if not text:
            continue
        if "|" in text:
            label, url = [part.strip() for part in text.split("|", 1)]
        else:
            label, url = "Shop related cards on eBay", text
        if not label:
            raise ValueError(f"Market brief affiliate link is missing a label: {path}")
        if not url.startswith("https://"):
            raise ValueError(f"Market brief affiliate link must be a complete https:// URL: {path}")
        links.append({"label": label, "url": url})
    return links


def render_market_brief_index(source_root: Path, output: Path) -> list[dict[str, object]]:
    source_dir = source_root / MARKET_BRIEF_SOURCE_DIR
    if not source_dir.exists():
        raise FileNotFoundError(f"Market brief content folder is missing: {source_dir}")
    posts: list[dict[str, object]] = []
    for path in sorted(source_dir.glob("*.md")):
        metadata, body = parse_markdown_frontmatter(path.read_text(encoding="utf-8-sig"), path)
        slug = str(metadata.get("slug", "") or path.stem).strip()
        title = str(metadata.get("title", "") or "").strip()
        summary = str(metadata.get("summary", "") or metadata.get("description", "") or "").strip()
        if not slug or not title or not summary:
            raise ValueError(f"Market brief requires slug, title, and summary: {path}")
        posts.append({
            "slug": slug,
            "label": str(metadata.get("label", "") or "Market Brief").strip(),
            "title": title,
            "date": str(metadata.get("date", "") or "").strip(),
            "author": str(metadata.get("author", "") or "Putnam Collectibles").strip(),
            "category": str(metadata.get("category", "") or "Pokemon Market Brief").strip(),
            "status": str(metadata.get("status", "") or "published").strip(),
            "summary": summary,
            "tags": metadata.get("tags", []),
            "affiliateLinks": parse_affiliate_links(metadata.get("affiliateLinks", []), path),
            "source_path": str((MARKET_BRIEF_SOURCE_DIR / path.name).as_posix()),
            "sections": markdown_sections(body),
        })
    posts.sort(key=lambda item: (str(item.get("date", "")), str(item.get("title", ""))), reverse=True)
    destination = output / MARKET_BRIEF_INDEX_FILE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"posts": posts}, indent=2) + "\n", encoding="utf-8")
    return posts


def write_generated_files(output: Path, commit: str, market_briefs: list[dict[str, object]]) -> None:
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "README.md").write_text(
        "\n".join([
            "# CardVector-site",
            "",
            "This repository is generated from `jhill2487/CardVector`.",
            "",
            "Do not edit this repository manually. Website source changes belong in:",
            "",
            "`CardVector/Docs/`",
            "",
            "Manual changes in this deployment repository may be overwritten by the next automated deployment.",
            "",
        ]),
        encoding="utf-8",
    )
    manifest = {
        "source_repository": "jhill2487/CardVector",
        "source_path": "Docs/",
        "source_commit": commit,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "public_files": list(PUBLIC_FILES),
        "public_assets": list(PUBLIC_ASSETS),
        "generated_content": [
            MARKET_BRIEF_INDEX_FILE.as_posix(),
            "market-briefs/index.html",
            "market-briefs/<slug>/index.html",
            "sitemap.xml",
        ],
        "market_brief_count": len(market_briefs),
    }
    (output / "deployment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def local_refs_from_text(text: str) -> set[str]:
    refs: set[str] = set()
    for match in re.finditer(r"""(?:src|href)=["']([^"']+)["']""", text, flags=re.IGNORECASE):
        refs.add(match.group(1))
    for match in re.finditer(r"""url\(["']?([^"')]+)["']?\)""", text, flags=re.IGNORECASE):
        refs.add(match.group(1))
    return refs


def normalize_public_ref(ref: str) -> str | None:
    if not ref or ref.startswith(("#", "http://", "https://", "mailto:", "tel:", "data:")):
        return None
    if ref.startswith("/"):
        ref = ref[1:]
    if "#" in ref:
        ref = ref.split("#", 1)[0]
    if "?" in ref:
        ref = ref.split("?", 1)[0]
    first_part = ref.split("/", 1)[0]
    if first_part in CLIENT_ROUTES and not Path(ref).suffix:
        return None
    return ref or None


def validate_references(output: Path) -> None:
    checked = [output / "index.html", output / "404.html", output / "style.css"]
    missing = []
    for path in checked:
        refs = local_refs_from_text(path.read_text(encoding="utf-8-sig"))
        for ref in refs:
            normalized = normalize_public_ref(ref)
            if normalized and not (output / normalized).exists():
                missing.append(f"{path.name}: {ref}")
    if missing:
        raise RuntimeError("Missing referenced public files:\n" + "\n".join(sorted(missing)))


def iter_output_files(output: Path) -> Iterable[Path]:
    for path in output.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            yield path


def validate_prohibited_files(output: Path) -> None:
    violations = []
    for path in iter_output_files(output):
        relative = path.relative_to(output)
        if any(part in PROHIBITED_PARTS for part in relative.parts):
            violations.append(str(relative))
        if path.suffix.lower() in PROHIBITED_SUFFIXES:
            violations.append(str(relative))
        text = ""
        if path.suffix.lower() in {".html", ".js", ".css", ".json", ".md", ".yml"}:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if "SUPABASE_SERVICE_ROLE_KEY" in text or "CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY" in text:
            violations.append(f"{relative}: service-role secret reference")
    if violations:
        raise RuntimeError("Prohibited files or secret references in public artifact:\n" + "\n".join(sorted(set(violations))))


def export_site(source: Path, output: Path, commit: str) -> None:
    site_config = load_site_config(source)
    clean_output(output)
    for relative in PUBLIC_FILES:
        copy_file(source, output, relative)
    for relative in PUBLIC_ASSETS:
        copy_file(source, output, relative)
    render_site_config(output, site_config)
    market_briefs = render_market_brief_index(source, output)
    render_market_brief_static_pages(output, market_briefs)
    render_sitemap(output, market_briefs)
    render_site_config(output, site_config)
    write_generated_files(output, commit, market_briefs)
    validate_references(output)
    validate_prohibited_files(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export the approved public CardVector static site artifact.")
    parser.add_argument("--source", type=Path, default=repo_root() / "Docs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    commit = source_commit(args.source_sha)
    export_site(args.source.resolve(), args.output.resolve(), commit)
    print(f"Exported CardVector public site from {commit} to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
