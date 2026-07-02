import unittest

from bend_score.utils.confidence import clamp_confidence, confidence_reason, weighted_confidence


class ConfidenceTest(unittest.TestCase):
    def test_confidence_helpers(self) -> None:
        self.assertEqual(clamp_confidence(120), 100)
        self.assertEqual(weighted_confidence([(90, 2), (60, 1)]), 80)
        self.assertTrue(confidence_reason(85, ["growth"]).startswith("High confidence"))


if __name__ == "__main__":
    unittest.main()

