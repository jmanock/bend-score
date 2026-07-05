import unittest

from bend_score.collectors.sample_data import sample_listings
from bend_score.recommendations import apply_recommendation


class RecommendationTest(unittest.TestCase):
    def test_apply_recommendation_sets_label_and_explanation(self) -> None:
        listing = apply_recommendation(sample_listings()[0])

        self.assertIsNotNone(listing.bend_score)
        self.assertIsNotNone(listing.founder_score)
        self.assertIsNotNone(listing.portfolio_fit)
        self.assertIn(
            listing.recommendation,
            {
                "★★★★★ BUILD NOW",
                "★★★★☆ ACQUIRE",
                "★★★★☆ BUILD LATER",
                "★★★☆☆ WATCH",
                "★★☆☆☆ RESEARCH",
                "★☆☆☆☆ IGNORE",
            },
        )
        self.assertTrue(listing.recommendation_explanation)
        self.assertTrue(listing.executive_summary)


if __name__ == "__main__":
    unittest.main()
