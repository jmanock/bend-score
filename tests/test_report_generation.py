import unittest

from bend_score.core.intelligence import IntelligenceRun
from bend_score.observers.fake_opportunity import FakeOpportunityObserver
from bend_score.observers.github import generate_github_signals
from bend_score.reports.markdown import build_intelligence_report


class ReportGenerationTest(unittest.TestCase):
    def test_intelligence_report_contains_v65_memo_sections(self) -> None:
        observer_result = FakeOpportunityObserver().run()
        intelligence = IntelligenceRun([observer_result], observer_result.signals)

        report = build_intelligence_report(intelligence, observer_result.signals, [], [])

        self.assertIn("# Bend Score Morning Investment Memo", report)
        self.assertIn("## Executive Summary", report)
        self.assertIn("## Consensus Opportunities", report)
        self.assertIn("## Today's Top 3", report)
        self.assertIn("## Observer Agreement", report)
        self.assertIn("## Heat Rankings", report)
        self.assertIn("## Portfolio Allocation", report)
        self.assertIn("## Executive Recommendation", report)
        self.assertIn("## Today's Movers", report)
        self.assertIn("## Opportunity Clusters", report)
        self.assertIn("## Suggested Build Roadmap", report)
        self.assertIn("## Feedback Notes", report)
        self.assertIn("## Full Opportunity Table", report)

    def test_report_includes_github_intelligence_sections(self) -> None:
        signals = generate_github_signals(
            {
                "repo_name": "agent-tool",
                "full_name": "octo/agent-tool",
                "html_url": "https://github.com/octo/agent-tool",
                "description": "AI agent automation workflow tool",
                "language": "Python",
                "stars": 2200,
                "forks": 240,
                "open_issues": 84,
                "watchers": 2200,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2026-06-01T00:00:00Z",
                "pushed_at": "2026-06-01T00:00:00Z",
                "license": "MIT",
                "topics": ["ai", "agent", "automation"],
                "owner": "octo",
                "archived": False,
                "homepage": "",
                "default_branch": "main",
                "query": "AI stars:>1000",
            }
        )
        intelligence = IntelligenceRun([], signals)

        report = build_intelligence_report(intelligence, signals, [], [])

        self.assertIn("## GitHub Intelligence", report)
        self.assertIn("### Fast Growing Repos", report)
        self.assertIn("### Commercial Potential", report)
        self.assertIn("### AI/Automation Tools", report)
        self.assertIn("### No Homepage Opportunities", report)
        self.assertIn("### High Issue Demand", report)


if __name__ == "__main__":
    unittest.main()
