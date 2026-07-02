import tempfile
import unittest
from pathlib import Path

from bend_score.collectors.sample_data import sample_listings
from bend_score.database.repository import ListingRepository
from bend_score.recommendations import apply_recommendation


class DatabaseTest(unittest.TestCase):
    def test_watchlist_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()
            repository.add_many(sample_listings()[:3])
            listings = [apply_recommendation(listing) for listing in repository.list_all()]
            repository.update_scores(listings)

            watched = repository.add_to_watchlist(1)
            noted = repository.append_note(1, "Review seller notes")
            stats = repository.stats()

            self.assertEqual(watched.status, "Watching")
            self.assertIn("Review seller notes", noted.notes)
            self.assertEqual(stats["total"], 3)
            self.assertGreater(stats["average_bend_score"], 0)
            self.assertEqual(len(repository.search("newsletter")), 1)


if __name__ == "__main__":
    unittest.main()
