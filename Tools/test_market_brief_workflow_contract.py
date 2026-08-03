import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "market-brief-draft.yml"
TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "market_brief_draft.yml"
SCRIPT = ROOT / "Tools" / "create_market_brief_from_issue.py"


class MarketBriefWorkflowContractTests(unittest.TestCase):
    def test_issue_template_exists_with_expected_label(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("content-draft", text)
        self.assertIn("monday-brief", text)
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


if __name__ == "__main__":
    unittest.main()
