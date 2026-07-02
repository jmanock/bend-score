import unittest

from bend_score.core.intelligence import IntelligenceRun
from bend_score.observers.fake_opportunity import FakeOpportunityObserver
from bend_score.reports.markdown import build_intelligence_report


class ReportGenerationTest(unittest.TestCase):
    def test_intelligence_report_contains_v3_sections(self) -> None:
        observer_result = FakeOpportunityObserver().run()
        intelligence = IntelligenceRun([observer_result], observer_result.signals)

        report = build_intelligence_report(intelligence, observer_result.signals, [], [])

        self.assertIn("# Today's Intelligence", report)
        self.assertIn("## High Confidence Signals", report)
        self.assertIn("## Observer Summary", report)
        self.assertIn("Fake Opportunity Observer", report)


if __name__ == "__main__":
    unittest.main()

