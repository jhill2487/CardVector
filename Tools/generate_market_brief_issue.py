from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SECTION_NAMES = ("PUBLISH_METADATA", "ARTICLE_FILE", "FACT_CHECK_NOTES", "TIKTOK_PACKAGE")
DEFAULT_MODEL = "gpt-5"
DEFAULT_PLAN = Path("Docs/content/market-briefs/content_plan.json")
DEFAULT_BRIEFS_DIR = Path("Docs/content/market-briefs")


class MarketBriefError(ValueError):
    pass


def today_utc() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "market-brief"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_content_plan(path: Path) -> dict[str, Any]:
    plan = read_json(path)
    topics = plan.get("topic_rotation")
    if not isinstance(topics, list) or not topics:
        raise MarketBriefError("Content plan must include a non-empty topic_rotation list.")
    return plan


def existing_market_brief_slugs(briefs_dir: Path) -> set[str]:
    slugs: set[str] = set()
    if not briefs_dir.exists():
        return slugs
    for path in sorted(briefs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            frontmatter = parse_markdown_frontmatter(text)
            slug = str(frontmatter.get("slug", "")).strip()
            if slug:
                slugs.add(slug)
        except MarketBriefError:
            for match in re.finditer(r"slug:\s*[\"']?([a-z0-9][a-z0-9-]+)", text):
                slugs.add(match.group(1))
        match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$", path.name)
        if match:
            slugs.add(match.group(1))
    return slugs


def existing_issue_slugs(issue_json: Path | None) -> set[str]:
    if not issue_json:
        return set()
    data = json.loads(issue_json.read_text(encoding="utf-8"))
    issues = data if isinstance(data, list) else data.get("issues", [])
    slugs: set[str] = set()
    for issue in issues:
        body = str(issue.get("body", "") if isinstance(issue, dict) else "")
        title = str(issue.get("title", "") if isinstance(issue, dict) else "")
        for text in (body, title):
            for match in re.finditer(r"slug:\s*[\"']?([a-z0-9][a-z0-9-]+)", text):
                slugs.add(match.group(1))
            for match in re.finditer(r"\b\d{4}-\d{2}-\d{2}-([a-z0-9][a-z0-9-]+)\.md\b", text):
                slugs.add(match.group(1))
    return slugs


def choose_topic(plan: dict[str, Any], brief_date: dt.date, used_slugs: set[str]) -> dict[str, Any]:
    topics = list(plan["topic_rotation"])
    start = int(brief_date.strftime("%U")) % len(topics)
    for offset in range(len(topics)):
        topic = topics[(start + offset) % len(topics)]
        key = slugify(str(topic.get("key", "")))
        if key and key not in used_slugs:
            return topic
    return topics[start]


def build_prompt(plan: dict[str, Any], topic: dict[str, Any], brief_date: dt.date, used_slugs: set[str]) -> str:
    used = ", ".join(sorted(used_slugs)) or "none"
    secondary = topic.get("secondary_keywords", [])
    return f"""Create CardVector's market brief publishing package in a deterministic format suitable for automated GitHub ingestion.

Return only one valid JSON object. Do not wrap the JSON in Markdown fences. Do not include any prose before or after the JSON.

The JSON object must contain these exact top-level keys:
- publishMetadata: an object with fields title, seoTitle, slug, date, excerpt, metaDescription, primaryKeyword, secondaryKeywords, category, tags, featuredImagePath, featuredImageAlt, socialTitle, socialDescription, status.
- filename: a deterministic filename in the format YYYY-MM-DD-<slug>.md.
- articleFile: one complete copy-paste-ready Markdown file as a JSON string, including YAML front matter and the final article body only. The string must start with "---\\n".
- factCheckNotes: a Markdown string listing time-sensitive claims, source names, source URLs, and source publication dates.
- tiktokPackage: a Markdown string with hook, 60-90 second voiceover, scene-by-scene B-roll, on-screen text, caption, hashtags, and CTA to CardVector.app.

Brief date: {brief_date.isoformat()}
Audience: {plan.get("audience")}
Topic angle: {topic.get("angle")}
Primary keyword: {topic.get("primary_keyword")}
Secondary keywords: {", ".join(str(item) for item in secondary)}
Existing slugs and filenames that must not be reused: {used}

Include recurring market-cycle education when relevant. Favor durable cyclical concepts over fragile predictions. Examples include summer slowdown, back-to-school spending shifts, holiday demand, tax refund season, new set release cycles, competitive rotation effects, payday or month-end buyer behavior, marketplace promotion cycles, and inventory aging cycles. Explain these as patterns sellers should monitor, not guaranteed buy/sell signals.

Write a polished 1,000-1,500 word SEO-focused article using evergreen seller education supported by current Pokemon, eBay, and TCGplayer developments. Emphasize durable trends and generalized recommendations. Avoid fragile buy/sell calls and exact prices unless essential. Do not place citations, drafting notes, placeholders, or instructions inside ARTICLE_FILE. Ensure all JSON, YAML, and Markdown are syntactically valid so a GitHub Action can parse and publish the article automatically.
"""


def market_brief_json_schema() -> dict[str, Any]:
    metadata_properties = {
        "title": {"type": "string"},
        "seoTitle": {"type": "string"},
        "slug": {"type": "string"},
        "date": {"type": "string"},
        "excerpt": {"type": "string"},
        "metaDescription": {"type": "string"},
        "primaryKeyword": {"type": "string"},
        "secondaryKeywords": {"type": "array", "items": {"type": "string"}},
        "category": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "featuredImagePath": {"type": "string"},
        "featuredImageAlt": {"type": "string"},
        "socialTitle": {"type": "string"},
        "socialDescription": {"type": "string"},
        "status": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "publishMetadata": {
                "type": "object",
                "additionalProperties": False,
                "properties": metadata_properties,
                "required": list(metadata_properties),
            },
            "filename": {"type": "string"},
            "articleFile": {"type": "string"},
            "factCheckNotes": {"type": "string"},
            "tiktokPackage": {"type": "string"},
        },
        "required": ["publishMetadata", "filename", "articleFile", "factCheckNotes", "tiktokPackage"],
    }


def call_openai_responses(prompt: str, model: str, use_web_search: bool) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or os.environ.get("OPEN_AI_KEY", "").strip()
    if not api_key:
        raise MarketBriefError("OPENAI_API_KEY or OPEN_AI_KEY is required to generate a market brief.")
    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cardvector_market_brief_package",
                "strict": True,
                "schema": market_brief_json_schema(),
            }
        },
    }
    if use_web_search:
        payload["tools"] = [{"type": "web_search"}]
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MarketBriefError(f"OpenAI API request failed with HTTP {exc.code}: {detail}") from exc
    text = str(data.get("output_text", "")).strip()
    if text:
        return text
    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(str(content.get("text", "")))
    text = "\n".join(part for part in chunks if part).strip()
    if not text:
        raise MarketBriefError("OpenAI API response did not include output text.")
    return text


def section_pattern(name: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*(?:#+\s*)?{re.escape(name)}\s*$", re.IGNORECASE | re.MULTILINE)


def yaml_quote(value: Any) -> str:
    return json.dumps(str(value or ""), ensure_ascii=False)


def normalize_article_markdown(article: str, metadata: dict[str, Any]) -> str:
    markdown = article.strip()
    if markdown.startswith("---\n"):
        return markdown + "\n"
    frontmatter_start = markdown.find("\n---\n")
    if frontmatter_start != -1:
        return markdown[frontmatter_start + 1 :].strip() + "\n"
    title = str(metadata.get("title") or "CardVector Market Brief").strip()
    slug = slugify(str(metadata.get("slug") or title))
    date = str(metadata.get("date") or today_utc().isoformat()).strip()
    description = str(metadata.get("metaDescription") or metadata.get("excerpt") or title).strip()
    category = str(metadata.get("category") or "Seller Strategy").strip()
    tags = metadata.get("tags")
    if not isinstance(tags, list):
        tags = ["Pokemon", "eBay", "TCGplayer"]
    frontmatter = [
        "---",
        f"title: {yaml_quote(title)}",
        f"seoTitle: {yaml_quote(metadata.get('seoTitle') or title)}",
        f"slug: {yaml_quote(slug)}",
        f"date: {yaml_quote(date)}",
        f"description: {yaml_quote(description)}",
        f"summary: {yaml_quote(metadata.get('excerpt') or description)}",
        'label: "Market Brief"',
        'author: "CardVector"',
        f"category: {yaml_quote(category)}",
        f"status: {yaml_quote(metadata.get('status') or 'draft')}",
        "tags:",
    ]
    frontmatter.extend(f"  - {yaml_quote(tag)}" for tag in tags)
    frontmatter.append("---")
    return "\n".join(frontmatter) + "\n\n" + markdown + "\n"


def parse_json_package(package_text: str) -> dict[str, str] | None:
    source = package_text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", source, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        source = fenced.group(1).strip()
    if not source.startswith("{"):
        return None
    try:
        data = json.loads(source)
    except json.JSONDecodeError:
        return None
    metadata = data.get("publishMetadata") or data.get("publish_metadata") or data.get("PUBLISH_METADATA")
    filename = str(data.get("filename", "")).strip()
    article = data.get("articleFile") or data.get("article_file") or data.get("ARTICLE_FILE")
    fact_check = data.get("factCheckNotes") or data.get("fact_check_notes") or data.get("FACT_CHECK_NOTES")
    tiktok = data.get("tiktokPackage") or data.get("tiktok_package") or data.get("TIKTOK_PACKAGE")
    if not isinstance(metadata, dict) or not isinstance(article, str):
        return None
    article_text = normalize_article_markdown(article, metadata)
    if filename:
        article_text = f"Filename: `{filename}`\n\n```markdown\n{article_text}```"
    return {
        "PUBLISH_METADATA": json.dumps(metadata, indent=2),
        "ARTICLE_FILE": article_text,
        "FACT_CHECK_NOTES": str(fact_check or "").strip(),
        "TIKTOK_PACKAGE": str(tiktok or "").strip(),
    }


def parse_sections(package_text: str) -> dict[str, str]:
    json_sections = parse_json_package(package_text)
    if json_sections:
        return json_sections
    matches: list[tuple[str, re.Match[str]]] = []
    for name in SECTION_NAMES:
        match = section_pattern(name).search(package_text)
        if not match:
            raise MarketBriefError(f"Missing required section: {name}")
        matches.append((name, match))
    matches.sort(key=lambda item: item[1].start())
    ordered = [name for name, _ in matches]
    if ordered != list(SECTION_NAMES):
        raise MarketBriefError("Publishing package sections are not in the required order.")
    sections: dict[str, str] = {}
    for index, (name, match) in enumerate(matches):
        start = match.end()
        end = matches[index + 1][1].start() if index + 1 < len(matches) else len(package_text)
        sections[name] = package_text[start:end].strip()
    return sections


def extract_json_object(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    source = fenced.group(1) if fenced else text
    start = source.find("{")
    end = source.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise MarketBriefError("PUBLISH_METADATA must contain a JSON object.")
    return json.loads(source[start : end + 1])


def extract_article_markdown(text: str) -> tuple[str, str]:
    filename_match = re.search(r"\b(\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md)\b", text)
    fenced_blocks = re.findall(r"```[a-zA-Z0-9_-]*\s*\n(.*?)\n```", text, flags=re.DOTALL)
    markdown = ""
    for block in fenced_blocks:
        candidate = block.strip() + "\n"
        if candidate.startswith("---\n"):
            markdown = candidate
            break
    if not markdown:
        bare = text.strip()
        if bare.startswith("---\n"):
            markdown = bare + "\n"
        else:
            frontmatter_start = bare.find("\n---\n")
            if frontmatter_start != -1:
                markdown = bare[frontmatter_start + 1 :].strip() + "\n"
    if not markdown:
        raise MarketBriefError("ARTICLE_FILE must contain the complete article Markdown starting with YAML front matter.")
    frontmatter = parse_markdown_frontmatter(markdown)
    filename = filename_match.group(1) if filename_match else f"{frontmatter['date']}-{frontmatter['slug']}.md"
    return filename, markdown


def parse_markdown_frontmatter(text: str) -> dict[str, Any]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    if not text.startswith("---\n"):
        raise MarketBriefError("Article Markdown must start with YAML front matter.")
    end = text.find("\n---", 4)
    if end == -1:
        raise MarketBriefError("Article Markdown front matter is not closed.")
    values: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in text[4:end].splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith("  - ") and current_list:
            values.setdefault(current_list, []).append(raw_line[4:].strip().strip("\"'"))
            continue
        current_list = None
        if ":" not in raw_line:
            raise MarketBriefError(f"Invalid YAML front matter line: {raw_line}")
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            values[key] = []
            current_list = key
        else:
            values[key] = value.strip("\"'")
    for required in ("title", "slug", "date", "description", "status"):
        if not str(values.get(required, "")).strip():
            raise MarketBriefError(f"Article front matter is missing required field: {required}")
    return values


def validate_package(package_text: str, brief_date: dt.date, existing_slugs: set[str]) -> dict[str, Any]:
    sections = parse_sections(package_text)
    metadata = extract_json_object(sections["PUBLISH_METADATA"])
    filename, markdown = extract_article_markdown(sections["ARTICLE_FILE"])
    frontmatter = parse_markdown_frontmatter(markdown)
    required_metadata = {
        "title",
        "seoTitle",
        "slug",
        "date",
        "excerpt",
        "metaDescription",
        "primaryKeyword",
        "secondaryKeywords",
        "category",
        "tags",
        "featuredImagePath",
        "featuredImageAlt",
        "socialTitle",
        "socialDescription",
        "status",
    }
    missing = sorted(required_metadata - set(metadata))
    if missing:
        raise MarketBriefError("PUBLISH_METADATA is missing required fields: " + ", ".join(missing))
    slug = str(metadata["slug"]).strip()
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise MarketBriefError("PUBLISH_METADATA.slug must be lowercase kebab-case.")
    if str(metadata["date"]) != brief_date.isoformat():
        raise MarketBriefError("PUBLISH_METADATA.date must match the workflow brief date.")
    if frontmatter["slug"] != slug:
        raise MarketBriefError("Article front matter slug must match PUBLISH_METADATA.slug.")
    if frontmatter["date"] != brief_date.isoformat():
        raise MarketBriefError("Article front matter date must match PUBLISH_METADATA.date.")
    expected_filename = f"{brief_date.isoformat()}-{slug}.md"
    if filename != expected_filename:
        raise MarketBriefError(f"ARTICLE_FILE filename must be {expected_filename}.")
    if slug in existing_slugs:
        raise MarketBriefError(f"Generated slug already exists: {slug}")
    if "```" in markdown:
        raise MarketBriefError("ARTICLE_FILE Markdown body must not contain nested fenced code blocks.")
    if len(re.findall(r"\b\w+\b", markdown)) < 900:
        raise MarketBriefError("ARTICLE_FILE appears too short for the required long-form brief.")
    return {
        "metadata": metadata,
        "filename": filename,
        "markdown": markdown,
        "frontmatter": frontmatter,
        "fact_check_notes": sections["FACT_CHECK_NOTES"],
        "tiktok_package": sections["TIKTOK_PACKAGE"],
    }


def build_issue_body(validated: dict[str, Any], package_text: str) -> str:
    filename = validated["filename"]
    markdown = validated["markdown"].rstrip()
    return f"""### Filename

`{filename}`

### Publishing package

```text
{package_text.strip()}
```

### Article file

```markdown
{markdown}
```

### Fact-check notes

{validated["fact_check_notes"].strip()}

### TikTok package

{validated["tiktok_package"].strip()}
"""


def issue_title(validated: dict[str, Any]) -> str:
    metadata = validated["metadata"]
    return f"[Content Draft] {metadata['title']} - {metadata['date']}"


def write_outputs(output_dir: Path, package_text: str, validated: dict[str, Any]) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / "market_brief_package.txt"
    issue_body_path = output_dir / "market_brief_issue_body.md"
    report_path = output_dir / "market_brief_generation_report.json"
    package_path.write_text(package_text.strip() + "\n", encoding="utf-8")
    issue_body_path.write_text(build_issue_body(validated, package_text), encoding="utf-8")
    report = {
        "title": issue_title(validated),
        "filename": validated["filename"],
        "slug": validated["metadata"]["slug"],
        "date": validated["metadata"]["date"],
        "labels": ["content-draft", "market-brief"],
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {
        "package": str(package_path),
        "issue_body": str(issue_body_path),
        "report": str(report_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and validate a CardVector market brief issue package.")
    parser.add_argument("--date", default=today_utc().isoformat(), help="Brief date in YYYY-MM-DD format.")
    parser.add_argument("--content-plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--briefs-dir", type=Path, default=DEFAULT_BRIEFS_DIR)
    parser.add_argument("--existing-issues-json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=os.environ.get("OPENAI_MARKET_BRIEF_MODEL", DEFAULT_MODEL))
    parser.add_argument("--input-package", type=Path, help="Validate an existing package instead of calling OpenAI.")
    parser.add_argument("--no-web-search", action="store_true", help="Disable OpenAI web_search tool for generation.")
    return parser


def run(args: argparse.Namespace) -> int:
    brief_date = dt.date.fromisoformat(args.date)
    plan = load_content_plan(args.content_plan)
    used_slugs = existing_market_brief_slugs(args.briefs_dir) | existing_issue_slugs(args.existing_issues_json)
    topic = choose_topic(plan, brief_date, used_slugs)
    if args.input_package:
        package_text = args.input_package.read_text(encoding="utf-8")
    else:
        prompt = build_prompt(plan, topic, brief_date, used_slugs)
        package_text = call_openai_responses(prompt, args.model, use_web_search=not args.no_web_search)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "market_brief_package.raw.txt").write_text(package_text, encoding="utf-8")
    try:
        validated = validate_package(package_text, brief_date, used_slugs)
    except MarketBriefError as exc:
        error_report = {
            "error": str(exc),
            "brief_date": brief_date.isoformat(),
            "topic": topic.get("key"),
            "raw_package": "market_brief_package.raw.txt",
        }
        (args.output_dir / "market_brief_generation_error.json").write_text(
            json.dumps(error_report, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    paths = write_outputs(args.output_dir, package_text, validated)
    print(json.dumps({"title": issue_title(validated), **paths}, indent=2))
    return 0


def main_for_test(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MarketBriefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
