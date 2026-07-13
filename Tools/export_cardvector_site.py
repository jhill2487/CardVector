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

CLIENT_ROUTES = {"about", "buylist", "bulk", "contact", "events", "etb", "location", "lot"}


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


def write_generated_files(output: Path, commit: str) -> None:
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
    clean_output(output)
    for relative in PUBLIC_FILES:
        copy_file(source, output, relative)
    for relative in PUBLIC_ASSETS:
        copy_file(source, output, relative)
    write_generated_files(output, commit)
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
