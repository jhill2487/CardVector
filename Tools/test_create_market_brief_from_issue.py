import json
import tempfile
import unittest
from pathlib import Path

from create_market_brief_from_issue import (
    build_market_brief_markdown,
    extract_fenced_markdown,
    parse_issue_sections,
    slugify,
    validate_article_markdown,
    write_market_brief,
)


class MarketBriefIssueImportTests(unittest.TestCase):
    def test_slugify_uses_safe_filename_text(self):
        self.assertEqual("pokemon-market-brief-august-3", slugify("Pokemon Market Brief: August 3!"))

    def test_parse_issue_form_sections(self):
        body = """### Brief date

2026-08-03

### Summary

Weekly market notes.

### Draft body

## What moved

Modern singles moved.
"""
        sections = parse_issue_sections(body)
        self.assertEqual("2026-08-03", sections["date"])
        self.assertEqual("Weekly market notes.", sections["summary"])
        self.assertIn("## What moved", sections["body"])

    def test_build_markdown_from_issue(self):
        issue = {
            "number": 42,
            "title": "Pokemon Market Brief: August 3",
            "url": "https://github.com/jhill2487/CardVector/issues/42",
            "body": """### Brief date

2026-08-03

### Slug

pokemon-market-brief-august-3

### Summary

Weekly market notes.

### Tags

Pokemon, Market Updates

### Draft body

## What moved

Modern singles moved.
""",
        }
        filename, content, report = build_market_brief_markdown(issue, "published")
        self.assertEqual("2026-08-03-pokemon-market-brief-august-3.md", filename)
        self.assertIn('title: "Pokemon Market Brief: August 3"', content)
        self.assertIn('sourceIssue: "#42"', content)
        self.assertIn("## What moved", content)
        self.assertEqual("pokemon-market-brief-august-3", report["slug"])

    def test_build_markdown_from_complete_fenced_article_file(self):
        issue = {
            "number": 84,
            "title": "[Content Draft] Pokemon Card Pricing Strategy - 2026-08-10",
            "url": "https://github.com/jhill2487/CardVector/issues/84",
            "body": """### Filename

`2026-08-10-pokemon-card-pricing-strategy.md`

### Article file

```markdown
---
title: "Pokemon Card Pricing Strategy"
slug: "pokemon-card-pricing-strategy"
date: "2026-08-10"
description: "Short SEO description and site teaser."
status: "published"
---

# Pokemon Card Pricing Strategy

Article content.
```

### Fact-check notes

Keep these in the issue only.
""",
        }
        filename, content, report = build_market_brief_markdown(issue, "published")
        self.assertEqual("2026-08-10-pokemon-card-pricing-strategy.md", filename)
        self.assertIn('description: "Short SEO description and site teaser."', content)
        self.assertNotIn("Fact-check notes", content)
        self.assertEqual("fenced_markdown", report["input_mode"])

    def test_validate_fenced_article_requires_frontmatter(self):
        with self.assertRaises(ValueError):
            validate_article_markdown("# Missing frontmatter")
        self.assertEqual("", extract_fenced_markdown("no fenced article"))

    def test_write_refuses_to_overwrite_different_existing_content(self):
        issue = {
            "number": 7,
            "title": "Pokemon Market Brief",
            "body": """### Brief date

2026-08-03

### Draft body

## What moved

Modern singles moved.
""",
        }
        with tempfile.TemporaryDirectory() as temp:
            issue_path = Path(temp) / "issue.json"
            output_dir = Path(temp) / "briefs"
            issue_path.write_text(json.dumps(issue), encoding="utf-8")
            output_path = write_market_brief(issue_path, output_dir, "published", None)
            output_path.write_text("different", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_market_brief(issue_path, output_dir, "published", None)


if __name__ == "__main__":
    unittest.main()
