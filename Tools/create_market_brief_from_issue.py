from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


KNOWN_SECTION_KEYS = {
    "brief date": "date",
    "date": "date",
    "slug": "slug",
    "summary": "summary",
    "label": "label",
    "author": "author",
    "category": "category",
    "tags": "tags",
    "draft body": "body",
    "body": "body",
    "brief": "body",
    "fact check notes": "fact_check_notes",
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "market-brief"


def clean_issue_value(value: str) -> str:
    value = value.strip()
    if value.lower() in {"_no response_", "no response"}:
        return ""
    return value


def normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_issue_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_heading = "body"
    sections[current_heading] = []
    for line in body.splitlines():
        match = re.match(r"^###\s+(.+?)\s*$", line)
        if match:
            normalized = normalize_heading(match.group(1))
            current_heading = KNOWN_SECTION_KEYS.get(normalized, normalized)
            sections.setdefault(current_heading, [])
            continue
        sections.setdefault(current_heading, []).append(line)
    return {key: clean_issue_value("\n".join(lines)) for key, lines in sections.items()}


def parse_tags(value: str) -> list[str]:
    tags: list[str] = []
    for part in re.split(r"[\n,]+", value):
        tag = part.strip().lstrip("-").strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_market_brief_markdown(issue: dict[str, Any], status: str) -> tuple[str, str, dict[str, Any]]:
    title = str(issue.get("title", "") or "Pokemon Market Brief").strip()
    body = str(issue.get("body", "") or "").strip()
    sections = parse_issue_sections(body)
    brief_body = sections.get("body") or body
    brief_date = sections.get("date") or date.today().isoformat()
    slug = slugify(sections.get("slug") or title)
    summary = sections.get("summary") or "Weekly Pokemon market update from Putnam Collectibles."
    label = sections.get("label") or "Weekly Monday Brief"
    author = sections.get("author") or "Putnam Collectibles"
    category = sections.get("category") or "Pokemon Market Brief"
    tags = parse_tags(sections.get("tags") or "Pokemon, Market Updates, Selling")
    issue_url = str(issue.get("url", "") or "").strip()
    issue_number = issue.get("number")

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", brief_date):
        raise ValueError("Brief date must use YYYY-MM-DD format.")
    if not brief_body:
        raise ValueError("Issue body must include draft body content.")

    frontmatter = [
        "---",
        f"title: {quoted(title)}",
        f"slug: {quoted(slug)}",
        f"date: {quoted(brief_date)}",
        f"label: {quoted(label)}",
        f"author: {quoted(author)}",
        f"category: {quoted(category)}",
        f"status: {quoted(status)}",
        f"summary: {quoted(summary)}",
        "tags:",
    ]
    frontmatter.extend(f"  - {tag}" for tag in tags)
    if issue_number:
        frontmatter.append(f"sourceIssue: {quoted(f'#{issue_number}')}")
    if issue_url:
        frontmatter.append(f"sourceUrl: {quoted(issue_url)}")
    frontmatter.append("---")

    content = "\n".join(frontmatter) + "\n\n" + brief_body.strip() + "\n"
    filename = f"{brief_date}-{slug}.md"
    report = {
        "title": title,
        "slug": slug,
        "date": brief_date,
        "status": status,
        "filename": filename,
        "source_issue": issue_number,
        "source_url": issue_url,
    }
    return filename, content, report


def write_market_brief(issue_json: Path, output_dir: Path, status: str, report_json: Path | None) -> Path:
    issue = json.loads(issue_json.read_text(encoding="utf-8"))
    filename, content, report = build_market_brief_markdown(issue, status)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    if output_path.exists() and output_path.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"Market brief already exists with different content: {output_path}")
    output_path.write_text(content, encoding="utf-8")
    report["output_path"] = output_path.as_posix()
    if report_json:
        report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Created market brief markdown: {output_path}")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a market brief markdown file from a GitHub issue draft.")
    parser.add_argument("--issue-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--status", default="published")
    parser.add_argument("--report-json", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    write_market_brief(args.issue_json, args.output_dir, args.status, args.report_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
