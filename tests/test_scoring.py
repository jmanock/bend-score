import unittest

from bend_score.models import Listing, utc_now
from bend_score.scoring.bend_score import calculate_bend_score, recommendation_for


class ScoringTest(unittest.TestCase):
    def test_content_site_with_traffic_and_low_revenue_scores_well(self) -> None:
        now = utc_now()
        listing = Listing(
            id=1,
            title="Useful Niche Blog",
            url="https://example.com",
            source="Test",
            category="Content Site",
            asking_price=5000,
            monthly_revenue=100,
            monthly_profit=90,
            traffic_estimate=20000,
            description="Thin comparison content with local SEO traction.",
            seller_notes="No affiliate strategy yet.",
            tech_stack="WordPress",
            created_at=now,
            updated_at=now,
        )

        result = calculate_bend_score(listing)

        self.assertGreaterEqual(result.total, 60)
        self.assertIn(result.recommendation, {"WATCH", "RESEARCH", "BUY"})
        self.assertIn("seo", result.components)
        self.assertIn("explanation", result.components["seo"])

    def test_recommendation_returns_label_and_explanation(self) -> None:
        label, explanation = recommendation_for(82, {"acquisition": {"score": 8}, "revenue": {"score": 7}})

        self.assertEqual(label, "BUY")
        self.assertTrue(explanation)


if __name__ == "__main__":
    unittest.main()
