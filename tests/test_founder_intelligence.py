import tempfile
import unittest
from pathlib import Path

from bend_score.collectors.sample_data import sample_listings
from bend_score.recommendations import apply_recommendation
from bend_score.reports.blueprints import build_project_blueprint, write_project_blueprints
from bend_score.scoring.founder_score import (
    analyze_founder_intelligence,
    calculate_founder_score,
    calculate_portfolio_fit,
    estimate_build_complexity,
    estimate_revenue_timeline,
    executive_summary_for,
    founder_recommendation,
)


class FounderIntelligenceTest(unittest.TestCase):
    def test_founder_score_returns_weighted_score_and_reasons(self) -> None:
        listing = sample_listings()[1]

        result = calculate_founder_score(listing)

        self.assertGreaterEqual(result.total, 60)
        self.assertIn("seo_scalability", result.factors)
        self.assertTrue(result.reasons)

    def test_portfolio_fit_scores_florida_content_highly(self) -> None:
        listing = sample_listings()[1]

        result = calculate_portfolio_fit(listing)

        self.assertGreaterEqual(result.score, 70)
        self.assertTrue(any("Florida Deals" in reason for reason in result.reasons))

    def test_blueprint_generation_includes_required_sections(self) -> None:
        listing = apply_recommendation(sample_listings()[0])

        content = build_project_blueprint(listing)

        self.assertIn("## Elevator Pitch", content)
        self.assertIn("## Suggested APIs", content)
        self.assertIn("## Expansion Roadmap", content)

    def test_blueprint_writer_creates_markdown_file(self) -> None:
        listing = apply_recommendation(sample_listings()[0])

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_project_blueprints([listing], Path(tmpdir))

            self.assertEqual(len(paths), 1)
            self.assertTrue(paths[0].exists())

    def test_recommendation_engine_uses_v6_labels(self) -> None:
        label, explanation = founder_recommendation(
            bend_score=82,
            founder_score=88,
            portfolio_fit=82,
            complexity="Small (1 week)",
            maintenance="Low: a few hours per month.",
        )

        self.assertEqual(label, "★★★★★ BUILD NOW")
        self.assertTrue(explanation)

    def test_complexity_estimator_returns_label_and_reason(self) -> None:
        listing = sample_listings()[9]

        result = estimate_build_complexity(listing)

        self.assertIn(result.label, {"Tiny (1-2 days)", "Small (1 week)", "Medium (2-4 weeks)", "Large", "Massive"})
        self.assertTrue(result.explanation)
        self.assertTrue(result.maintenance)

    def test_executive_summary_generation_mentions_action(self) -> None:
        summary = executive_summary_for(
            sample_listings()[0],
            "★★★★★ BUILD NOW",
            founder_score=91,
            portfolio_fit=85,
            complexity="Small (1 week)",
            timeline="1 month",
        )

        self.assertIn("Recommended action: BUILD NOW", summary)

    def test_full_founder_intelligence_bundle(self) -> None:
        listing = sample_listings()[0]

        result = analyze_founder_intelligence(listing, bend_score=80)

        self.assertGreater(result.founder_score.total, 0)
        self.assertGreater(result.portfolio_fit.score, 0)
        self.assertTrue(result.executive_summary)
        self.assertTrue(result.recommendation)

    def test_revenue_timeline_uses_existing_revenue(self) -> None:
        listing = sample_listings()[0]

        result = estimate_revenue_timeline(listing)

        self.assertEqual(result.label, "1 month")


if __name__ == "__main__":
    unittest.main()
