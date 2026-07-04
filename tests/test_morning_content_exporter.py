from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from bend_score.exporters.morning_content import export_opportunities, should_export, signal_for_listing
from bend_score.models import Listing, utc_now
from bend_score.recommendations import apply_recommendation


class MorningContentExporterTest(unittest.TestCase):
    def test_exporter_creates_valid_signal_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            listing = apply_recommendation(_listing(id=42, bend_score=None, recommendation=None))
            summary = export_opportunities([listing], Path(tmpdir), export_date=date(2026, 7, 4))

            self.assertEqual(summary.exported, 1)
            signal = json.loads(summary.files[0].read_text(encoding="utf-8"))
            required = {
                "source_project",
                "source_type",
                "brand",
                "title",
                "summary",
                "url",
                "category",
                "priority",
                "confidence",
            }
            self.assertTrue(required <= signal.keys())
            self.assertEqual(signal["source_project"], "bend-score")
            self.assertEqual(signal["brand"], "Bend Score")
            self.assertEqual(signal["source_type"], "opportunity")
            self.assertTrue(1 <= signal["priority"] <= 10)
            self.assertTrue(0 <= signal["confidence"] <= 100)

    def test_ignore_and_pass_items_are_not_exported(self) -> None:
        ignore = _listing(id=1, bend_score=20, recommendation="IGNORE")
        passed = _listing(id=2, bend_score=90, recommendation="PASS")

        self.assertFalse(should_export(ignore))
        self.assertFalse(should_export(passed))

    def test_duplicate_prevention_uses_stable_daily_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            listing = apply_recommendation(_listing(id=7))
            first = export_opportunities([listing], Path(tmpdir), export_date=date(2026, 7, 4))
            second = export_opportunities([listing], Path(tmpdir), export_date=date(2026, 7, 4))

            self.assertEqual(first.exported, 1)
            self.assertEqual(second.exported, 0)
            self.assertEqual(second.duplicates, 1)
            self.assertEqual(len(list(Path(tmpdir).glob("*.json"))), 1)

    def test_metadata_includes_original_listing_and_score_breakdown(self) -> None:
        listing = apply_recommendation(_listing(id=99))
        signal = signal_for_listing(listing, export_date=date(2026, 7, 4))
        metadata = signal["metadata"]

        self.assertEqual(metadata["original_listing_id"], 99)
        self.assertIn("bend_score", metadata)
        self.assertIn("recommendation", metadata)
        self.assertIn("asking_price", metadata)
        self.assertIn("monthly_revenue", metadata)
        self.assertIn("monthly_profit", metadata)
        self.assertIn("source", metadata)
        self.assertIn("category", metadata)
        self.assertIn("score_breakdown", metadata)


def _listing(
    id: int | None = 1,
    bend_score: float | None = 82,
    recommendation: str | None = "RESEARCH",
) -> Listing:
    now = utc_now()
    return Listing(
        id=id,
        title="Undervalued SaaS with automation upside",
        url="https://example.com/listing/automation-saas",
        source="Acquire",
        category="SaaS",
        asking_price=25000,
        monthly_revenue=3200,
        monthly_profit=1800,
        traffic_estimate=9000,
        description="A niche SaaS product with manual workflows and automation upside.",
        seller_notes="Owner spends only a few hours each week.",
        tech_stack="Python, Stripe, React",
        created_at=now,
        updated_at=now,
        bend_score=bend_score,
        recommendation=recommendation,
        recommendation_explanation="Promising upside signal deserves deeper diligence before action.",
    )


if __name__ == "__main__":
    unittest.main()

