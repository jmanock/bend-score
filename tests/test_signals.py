import unittest

from bend_score.models import Signal, normalize_recommendation


class SignalTest(unittest.TestCase):
    def test_signal_normalizes_confidence_impact_and_recommendation(self) -> None:
        signal = Signal.create(
            observer="test",
            signal_type="growth",
            title="Test Growth",
            description="A useful signal.",
            category="SaaS",
            confidence=150,
            impact="giant",
            recommendation="pass",
            metadata={"stars": 120},
        )

        self.assertEqual(signal.confidence, 100)
        self.assertEqual(signal.impact, "medium")
        self.assertEqual(signal.recommendation, "IGNORE")
        self.assertIn('"stars": 120', signal.metadata_json())

    def test_recommendation_mapping(self) -> None:
        self.assertEqual(normalize_recommendation("investigate"), "RESEARCH")
        self.assertEqual(normalize_recommendation("monitor"), "WATCH")


if __name__ == "__main__":
    unittest.main()

