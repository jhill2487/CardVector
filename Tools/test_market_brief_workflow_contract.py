import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "market-brief-draft.yml"
GENERATE_WORKFLOW = ROOT / ".github" / "workflows" / "generate-market-brief-issue.yml"
TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "market_brief_draft.yml"
SCRIPT = ROOT / "Tools" / "create_market_brief_from_issue.py"
GENERATOR = ROOT / "Tools" / "generate_market_brief_issue.py"
CONTENT_PLAN = ROOT / "Docs" / "content" / "market-briefs" / "content_plan.json"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_market_brief_issue", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


SAMPLE_PACKAGE = """
PUBLISH_METADATA
{
  "title": "Seasonal Pokemon Card Market Trends Sellers Should Track",
  "seoTitle": "Pokemon Card Seasonal Market Trends for Sellers",
  "slug": "seasonal-pokemon-card-market-trends",
  "date": "2026-08-17",
  "excerpt": "Learn how recurring seasonal trends can shape Pokemon card seller workflows.",
  "metaDescription": "Pokemon card sellers can use seasonal market trends to plan pricing, inventory review, and listing quality work.",
  "primaryKeyword": "Pokemon card seasonal market trends",
  "secondaryKeywords": ["summer slump", "holiday demand"],
  "category": "Seller Strategy",
  "tags": ["Pokemon", "eBay", "TCGplayer"],
  "featuredImagePath": "/images/blog/seasonal-pokemon-card-market-trends.webp",
  "featuredImageAlt": "Pokemon cards organized for seasonal market review",
  "socialTitle": "Pokemon Card Seasonal Trends Sellers Should Track",
  "socialDescription": "A seller guide to seasonal Pokemon card market patterns.",
  "status": "draft"
}
ARTICLE_FILE
Filename: `2026-08-17-seasonal-pokemon-card-market-trends.md`

```markdown
---
title: "Seasonal Pokemon Card Market Trends Sellers Should Track"
seoTitle: "Pokemon Card Seasonal Market Trends for Sellers"
slug: "seasonal-pokemon-card-market-trends"
date: "2026-08-17"
description: "Pokemon card sellers can use seasonal market trends to plan pricing, inventory review, and listing quality work."
summary: "Learn how recurring seasonal trends can shape Pokemon card seller workflows."
label: "Market Brief"
author: "CardVector"
category: "Seller Strategy"
status: "draft"
tags:
  - Pokemon
  - eBay
  - TCGplayer
---

# Seasonal Pokemon Card Market Trends Sellers Should Track

""" + "Market cycles help sellers plan inventory review and pricing discipline. " * 180 + """
```
FACT_CHECK_NOTES
- Time-sensitive claim: Seasonal patterns are discussed as general seller education.
  - Source name: Example source
  - Source URL: https://example.com
  - Source publication date: 2026-08-17
TIKTOK_PACKAGE
Hook: Watch seasonal card market cycles.
Voiceover: Sellers should understand seasonal cycles before they panic reprice inventory.
B-roll: Cards, listings, calendar, seller dashboard.
On-screen text: Seasonal trends are signals, not guarantees.
Caption: A quick seller note on seasonal Pokemon card market trends.
Hashtags: #PokemonCards #CardSeller
CTA: Read more at CardVector.app.
"""


class MarketBriefWorkflowContractTests(unittest.TestCase):
    def test_issue_template_exists_with_expected_label(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("content-draft", text)
        self.assertIn("market-brief", text)
        self.assertIn("Filename", text)
        self.assertIn("Article file", text)
        self.assertIn("Fact-check notes", text)
        self.assertIn("TikTok package", text)

    def test_workflow_creates_draft_pull_request_from_issue(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("issues:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("ready-for-pr", text)
        self.assertNotIn("github.event.label.name == 'market-brief-draft'", text)
        self.assertIn("Tools/create_market_brief_from_issue.py", text)
        self.assertIn("--draft", text)
        self.assertIn("Docs/content/market-briefs", text)
        self.assertIn("Tools/export_cardvector_site.py", text)

    def test_market_brief_script_does_not_depend_on_github_runtime(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--issue-json", text)
        self.assertIn("--output-dir", text)
        self.assertNotIn("GH_TOKEN", text)
        self.assertNotIn("subprocess", text)

    def test_scheduled_generator_workflow_creates_issue_not_pr(self):
        text = GENERATE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("schedule:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("issues: write", text)
        self.assertIn("OPENAI_API_KEY", text)
        self.assertIn("OPEN_AI_KEY", text)
        self.assertIn("Tools/generate_market_brief_issue.py", text)
        self.assertIn("gh issue create", text)
        self.assertIn("--label content-draft", text)
        self.assertIn("--label market-brief", text)
        self.assertNotIn("gh pr create", text)

    def test_content_plan_exists_with_topic_rotation(self):
        text = CONTENT_PLAN.read_text(encoding="utf-8")
        self.assertIn("topic_rotation", text)
        self.assertIn("seasonal-summer-slump", text)
        self.assertIn("holiday-demand-cycle", text)
        self.assertIn("back-to-school-shift", text)
        self.assertIn("new-set-release-cycle", text)

    def test_generator_uses_strict_openai_schema(self):
        generator = load_generator_module()
        schema = generator.market_brief_json_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("publishMetadata", schema["required"])
        self.assertIn("articleFile", schema["required"])
        self.assertFalse(schema["properties"]["publishMetadata"]["additionalProperties"])

    def test_generator_reads_crlf_frontmatter(self):
        generator = load_generator_module()
        markdown = "---\r\ntitle: \"Existing Brief\"\r\nslug: \"existing-brief\"\r\ndate: \"2026-08-17\"\r\ndescription: \"Existing brief.\"\r\nstatus: \"published\"\r\n---\r\n\r\n# Existing Brief\r\n"
        frontmatter = generator.parse_markdown_frontmatter(markdown)
        self.assertEqual("existing-brief", frontmatter["slug"])

    def test_existing_slug_discovery_tolerates_historical_files(self):
        generator = load_generator_module()
        with tempfile.TemporaryDirectory() as temp:
            briefs = Path(temp)
            (briefs / "2026-08-17-historical-brief.md").write_text(
                "\ufeff\nslug: \"historical-brief\"\n# Historical Brief\n",
                encoding="utf-8",
            )
            slugs = generator.existing_market_brief_slugs(briefs)
            self.assertIn("historical-brief", slugs)

    def test_existing_issue_slugs_accepts_github_cli_array(self):
        generator = load_generator_module()
        with tempfile.TemporaryDirectory() as temp:
            issues = Path(temp) / "issues.json"
            issues.write_text(json.dumps([{
                "number": 7,
                "title": "[Content Draft] Example - 2026-08-18",
                "body": "Filename: `2026-08-18-example-market-brief.md`\nslug: \"example-market-brief\"",
            }]), encoding="utf-8")
            slugs = generator.existing_issue_slugs(issues)
            self.assertIn("example-market-brief", slugs)

    def test_generator_validates_package_and_builds_issue_body(self):
        generator = load_generator_module()
        validated = generator.validate_package(SAMPLE_PACKAGE, dt.date(2026, 8, 17), set())
        body = generator.build_issue_body(validated, SAMPLE_PACKAGE)
        self.assertEqual("2026-08-17-seasonal-pokemon-card-market-trends.md", validated["filename"])
        self.assertIn("### Article file", body)
        self.assertIn("```markdown", body)
        self.assertIn("### Fact-check notes", body)
        self.assertIn("### TikTok package", body)

    def test_generator_selects_frontmatter_markdown_block(self):
        generator = load_generator_module()
        package = SAMPLE_PACKAGE.replace(
            "2026-08-17-seasonal-pokemon-card-market-trends.md\n\n```markdown",
            "2026-08-17-seasonal-pokemon-card-market-trends.md\n\n```text\nDo not parse this helper block.\n```\n\n```markdown",
        )
        validated = generator.validate_package(package, dt.date(2026, 8, 17), set())
        self.assertTrue(validated["markdown"].startswith("---\n"))

    def test_generator_accepts_bare_article_frontmatter(self):
        generator = load_generator_module()
        package = SAMPLE_PACKAGE.replace("```markdown\n", "", 1)
        article_end = package.index("\n```\nFACT_CHECK_NOTES")
        package = package[:article_end] + package[article_end + len("\n```") :]
        validated = generator.validate_package(package, dt.date(2026, 8, 17), set())
        self.assertEqual("seasonal-pokemon-card-market-trends", validated["metadata"]["slug"])

    def test_generator_accepts_json_package_contract(self):
        generator = load_generator_module()
        section_validated = generator.validate_package(SAMPLE_PACKAGE, dt.date(2026, 8, 17), set())
        package = json.dumps({
            "publishMetadata": section_validated["metadata"],
            "filename": section_validated["filename"],
            "articleFile": section_validated["markdown"],
            "factCheckNotes": section_validated["fact_check_notes"],
            "tiktokPackage": section_validated["tiktok_package"],
        })
        validated = generator.validate_package(package, dt.date(2026, 8, 17), set())
        self.assertEqual(section_validated["filename"], validated["filename"])
        self.assertTrue(validated["markdown"].startswith("---\n"))

    def test_generator_synthesizes_frontmatter_for_json_article_body(self):
        generator = load_generator_module()
        section_validated = generator.validate_package(SAMPLE_PACKAGE, dt.date(2026, 8, 17), set())
        body_only = "# Seasonal Pokemon Card Market Trends Sellers Should Track\n\n" + (
            "Market cycles help sellers plan inventory review and pricing discipline. " * 180
        )
        package = json.dumps({
            "publishMetadata": section_validated["metadata"],
            "filename": section_validated["filename"],
            "articleFile": body_only,
            "factCheckNotes": section_validated["fact_check_notes"],
            "tiktokPackage": section_validated["tiktok_package"],
        })
        validated = generator.validate_package(package, dt.date(2026, 8, 17), set())
        self.assertTrue(validated["markdown"].startswith("---\n"))
        self.assertEqual("seasonal-pokemon-card-market-trends", validated["frontmatter"]["slug"])

    def test_generator_rejects_duplicate_slug(self):
        generator = load_generator_module()
        with self.assertRaisesRegex(Exception, "already exists"):
            generator.validate_package(
                SAMPLE_PACKAGE,
                dt.date(2026, 8, 17),
                {"seasonal-pokemon-card-market-trends"},
            )

    def test_generator_cli_can_validate_without_openai_api_call(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            package = temp_path / "package.txt"
            output = temp_path / "out"
            package.write_text(SAMPLE_PACKAGE, encoding="utf-8")
            generator = load_generator_module()
            code = generator.main_for_test([
                "--date",
                "2026-08-17",
                "--content-plan",
                str(CONTENT_PLAN),
                "--briefs-dir",
                str(temp_path / "briefs"),
                "--input-package",
                str(package),
                "--output-dir",
                str(output),
            ])
            self.assertEqual(0, code)
            self.assertTrue((output / "market_brief_issue_body.md").exists())


if __name__ == "__main__":
    unittest.main()
