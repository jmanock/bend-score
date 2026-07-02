import tempfile
import unittest
from pathlib import Path

from bend_score.database.repository import ListingRepository
from bend_score.models import Signal


class TimelineStorageTest(unittest.TestCase):
    def test_insert_signals_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()
            signal = Signal.create(
                observer="test",
                signal_type="repository_growth",
                title="GitHub Growth",
                description="Stars increased.",
                category="GitHub",
                confidence=91,
                impact="high",
                recommendation="WATCH",
                metadata={"stars": 138},
            )

            repository.insert_signals([signal])
            repository.insert_signals([signal])
            stats = repository.signal_stats()

            self.assertEqual(stats["signals"], 2)
            self.assertEqual(stats["history"], 2)
            self.assertEqual(stats["highest_confidence"], 91)


if __name__ == "__main__":
    unittest.main()

