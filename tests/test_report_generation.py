import unittest

from bend_score.core.intelligence import IntelligenceRun
from bend_score.observers.fake_opportunity import FakeOpportunityObserver
from bend_score.reports.markdown import build_intelligence_report


class ReportGenerationTest(unittest.TestCase):
    def test_intelligence_report_contains_v65_memo_sections(self) -> None:
        observer_result = FakeOpportunityObserver().run()
        intelligence = IntelligenceRun([observer_result], observer_result.signals)

        report = build_intelligence_report(intelligence, observer_result.signals, [], [])

        self.assertIn("# Bend Score Morning Investment Memo", report)
        self.assertIn("## Executive Summary", report)
        self.assertIn("## Today's Top 3 Opportunities", report)
        self.assertIn("## Today's Movers", report)
        self.assertIn("## Opportunity Clusters", report)
        self.assertIn("## Suggested Build Roadmap", report)
        self.assertIn("## Feedback Notes", report)
        self.assertIn("## Full Opportunity Table", report)


if __name__ == "__main__":
    unittest.main()
