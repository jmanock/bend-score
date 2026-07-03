import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bend_score import app, ui
from bend_score.database.repository import ListingRepository
from bend_score.intake.listings import listing_from_mapping
from bend_score.intake.validation import normalize_source, parse_number, validate_url


class IntakeTest(unittest.TestCase):
    def test_csv_import_and_duplicate_detection(self) -> None:
        csv_text = """title,url,source,category,asking_price,monthly_revenue,monthly_profit,traffic_estimate,description,seller_notes,tech_stack
Test SaaS,https://example.com/test-saas,Acquire,SaaS,12000,900,700,3000,Niche SaaS,Dated onboarding,Django Stripe
Bad Price,https://example.com/bad,Flippa,Content Site,not-money,100,80,5000,Bad row,,
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "listings.csv"
            path.write_text(csv_text, encoding="utf-8")
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()

            first = app.import_csv_file(path, repository)
            second = app.import_csv_file(path, repository)

            self.assertEqual(first.rows_processed, 2)
            self.assertEqual(len(first.imported), 1)
            self.assertEqual(len(first.errors), 1)
            self.assertEqual(second.duplicates_skipped, 1)

    def test_manual_listing_creation_logic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()

            listing = app.create_manual_listing(
                {
                    "title": "Manual Newsletter",
                    "url": "",
                    "source": "",
                    "category": "Newsletter",
                    "asking_price": "5000",
                    "monthly_revenue": "250",
                    "monthly_profit": "200",
                    "traffic_estimate": "4200",
                    "description": "Small niche newsletter",
                    "seller_notes": "No sponsor automation",
                },
                repository,
            )

            self.assertEqual(listing.source, "Manual")
            self.assertIsNotNone(listing.id)
            self.assertGreater(listing.bend_score, 0)

    def test_validation_helpers(self) -> None:
        self.assertEqual(normalize_source("Acquire.com"), "Acquire")
        self.assertEqual(normalize_source("Unknown Marketplace"), "Other")
        self.assertEqual(parse_number("$1,200", "asking_price"), 1200)
        self.assertEqual(validate_url(""), "")
        with self.assertRaises(ValueError):
            parse_number("abc", "monthly_revenue")
        with self.assertRaises(ValueError):
            validate_url("example.com/listing")

    def test_listing_detail_output(self) -> None:
        listing = listing_from_mapping(
            {
                "title": "Detail SaaS",
                "url": "https://example.com/detail",
                "source": "Microns",
                "category": "SaaS",
                "asking_price": "15000",
                "monthly_revenue": "1000",
                "monthly_profit": "800",
                "traffic_estimate": "2500",
                "description": "Useful product",
                "seller_notes": "Plain design",
                "tech_stack": "Rails Stripe",
            }
        )
        listing.id = 99
        output = io.StringIO()

        with redirect_stdout(output):
            ui.print_listing_detail(listing, "Watching")

        rendered = output.getvalue()
        self.assertIn("Detail SaaS", rendered)
        self.assertIn("Score breakdown", rendered)
        self.assertIn("Watchlist status: Watching", rendered)


if __name__ == "__main__":
    unittest.main()
