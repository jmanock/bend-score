import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bend_score import app
from bend_score.collectors.sample_data import sample_listings
from bend_score.database.repository import ListingRepository
from bend_score.exporters.morning_content import signal_for_listing
from bend_score.memory import (
    ScoreSnapshot,
    build_roadmap,
    detect_clusters,
    feedback_summary_for_listing,
    trend_for_memory,
)
from bend_score.recommendations import apply_recommendation


class OpportunityMemoryTest(unittest.TestCase):
    def test_opportunity_memory_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()
            listing = apply_recommendation(sample_listings()[0])
            repository.add_listing(listing)

            repository.record_opportunity_memory(repository.list_all())
            repository.record_opportunity_memory(repository.list_all())

            memory = repository.get_opportunity_memory(1)
            self.assertIsNotNone(memory)
            self.assertEqual(memory.times_seen, 2)
            self.assertEqual(len(memory.history), 2)

    def test_trend_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()
            listing = apply_recommendation(sample_listings()[0])
            repository.add_listing(listing)
            repository.record_opportunity_memory(repository.list_all())
            listing.founder_score = (listing.founder_score or 0) + 8
            listing.bend_score = (listing.bend_score or 0) + 2
            repository.update_scores([listing])
            repository.record_opportunity_memory(repository.list_all())

            trend = trend_for_memory(repository.get_opportunity_memory(1))

            self.assertEqual(trend.label, "RISING")
            self.assertGreater(trend.founder_score_change, 0)

    def test_feedback_storage_and_feedback_adjustment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()
            listing = apply_recommendation(sample_listings()[1])
            repository.add_listing(listing)

            repository.add_feedback(1, "love", "Good fit")
            feedback = repository.list_feedback()
            adjusted = apply_recommendation(repository.get_listing(1), feedback)
            summary = feedback_summary_for_listing(adjusted, feedback)

            self.assertEqual(len(feedback), 1)
            self.assertGreater(summary.founder_adjustment, 0)
            self.assertIn("Founder feedback", adjusted.recommendation_explanation)

    def test_opportunity_clusters(self) -> None:
        listings = []
        for index, listing in enumerate(sample_listings(), start=1):
            listing.id = index
            listings.append(apply_recommendation(listing))

        clusters = detect_clusters(listings)

        self.assertTrue(clusters)
        self.assertGreaterEqual(len(clusters[0].listings), 2)

    def test_roadmap_generation(self) -> None:
        listings = [apply_recommendation(listing) for listing in sample_listings()[:5]]

        roadmap = build_roadmap(listings, [], [])

        self.assertEqual(len(roadmap), 5)
        self.assertIn(roadmap[0].action, {"build now", "build later", "watch"})
        self.assertTrue(roadmap[0].next_action)

    def test_signal_export_includes_trend_metadata(self) -> None:
        listing = apply_recommendation(sample_listings()[0])
        listing.id = 1
        memory = app_memory(listing)

        signal = signal_for_listing(listing, memory=memory)

        self.assertIn("founder_score", signal["metadata"])
        self.assertIn("trend", signal["metadata"])
        self.assertEqual(signal["metadata"]["trend"], "RISING")

    def test_opportunity_detail_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original = app.ListingRepository
            try:
                db_path = Path(tmpdir) / "bend_score.sqlite3"

                class TempRepository(ListingRepository):
                    def __init__(self) -> None:
                        super().__init__(db_path)

                app.ListingRepository = TempRepository
                repository = TempRepository()
                repository.create_schema()
                listing = apply_recommendation(sample_listings()[0])
                repository.add_listing(listing)
                repository.record_opportunity_memory(repository.list_all())

                output = io.StringIO()
                with redirect_stdout(output):
                    app.opportunity_detail(1)

                self.assertIn("Score history:", output.getvalue())
                self.assertIn("Blueprint path:", output.getvalue())
            finally:
                app.ListingRepository = original


def app_memory(listing):
    from bend_score.memory import OpportunityMemory

    return OpportunityMemory(
        listing_id=listing.id,
        first_seen="2026-07-01T00:00:00+00:00",
        last_seen="2026-07-02T00:00:00+00:00",
        title=listing.title,
        category=listing.category,
        source=listing.source,
        current_bend_score=listing.bend_score or 0,
        current_founder_score=listing.founder_score or 0,
        current_recommendation=listing.recommendation or "",
        times_seen=2,
        notes="",
        history=[
            ScoreSnapshot("2026-07-01T00:00:00+00:00", (listing.bend_score or 0) - 5, (listing.founder_score or 0) - 3, "WATCH"),
            ScoreSnapshot("2026-07-02T00:00:00+00:00", listing.bend_score or 0, listing.founder_score or 0, listing.recommendation or ""),
        ],
    )


if __name__ == "__main__":
    unittest.main()
