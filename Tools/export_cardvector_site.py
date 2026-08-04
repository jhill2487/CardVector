from __future__ import annotations

import argparse
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
SITE_CONFIG_KEYS = (
    "EBAY_STORE_URL",
    "TCGPLAYER_STORE_URL",
    "WHATNOT_REFERRAL_URL",
    "WHATNOT_SELLER_REFERRAL_URL",
    "COLLECTION_INQUIRY_URL",
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
    "sell",
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
        if not value.startswith("https://"):
            raise ValueError(f"{key} must be a complete https:// URL.")
        if "PASTE_" in value.upper() or "PLACEHOLDER" in value.upper():
            raise ValueError(f"{key} still contains a placeholder value.")
        config[key] = value
    return config


def render_site_config(output: Path, config: dict[str, str]) -> None:
    token_pattern = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
    for relative in ("index.html", "404.html", "app.js"):
        path = output / relative
        text = path.read_text(encoding="utf-8-sig")
        for key, value in config.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        unresolved = sorted(set(token_pattern.findall(text)))
        if unresolved:
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
        "generated_content": [MARKET_BRIEF_INDEX_FILE.as_posix()],
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
