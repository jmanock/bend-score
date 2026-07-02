from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from bend_score.config import DATABASE_PATH
from bend_score.models import Listing, WatchlistItem, utc_now
from bend_score.scoring.common import revenue_multiple


DEFAULT_DB_PATH = DATABASE_PATH
WATCHLIST_STATUSES = {"Watching", "Researching", "Interested", "Contacted", "Passed", "Purchased"}


class ListingRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_schema(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    asking_price REAL NOT NULL DEFAULT 0,
                    monthly_revenue REAL NOT NULL DEFAULT 0,
                    monthly_profit REAL NOT NULL DEFAULT 0,
                    traffic_estimate INTEGER NOT NULL DEFAULT 0,
                    description TEXT NOT NULL DEFAULT '',
                    seller_notes TEXT NOT NULL DEFAULT '',
                    tech_stack TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    bend_score REAL,
                    recommendation TEXT,
                    recommendation_explanation TEXT
                )
                """
            )
            self._add_column_if_missing(connection, "listings", "recommendation_explanation", "TEXT")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    date_added TEXT NOT NULL,
                    date_updated TEXT NOT NULL,
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                )
                """
            )

    def _add_column_if_missing(
        self, connection: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        columns = [row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in columns:
            try:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

    def count(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM listings").fetchone()
            return int(row["count"])

    def add_many(self, listings: Iterable[Listing]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO listings (
                    title, url, source, category, asking_price, monthly_revenue,
                    monthly_profit, traffic_estimate, description, seller_notes,
                    tech_stack, created_at, updated_at, bend_score, recommendation
                )
                VALUES (
                    :title, :url, :source, :category, :asking_price, :monthly_revenue,
                    :monthly_profit, :traffic_estimate, :description, :seller_notes,
                    :tech_stack, :created_at, :updated_at, :bend_score, :recommendation
                )
                """,
                [listing.__dict__ for listing in listings],
            )

    def list_all(self) -> list[Listing]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM listings ORDER BY id").fetchall()
            return [Listing.from_row(row) for row in rows]

    def update_scores(self, listings: Iterable[Listing]) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.executemany(
                """
                UPDATE listings
                SET bend_score = :bend_score,
                    recommendation = :recommendation,
                    recommendation_explanation = :recommendation_explanation,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                [
                    {
                        "id": listing.id,
                        "bend_score": listing.bend_score,
                        "recommendation": listing.recommendation,
                        "recommendation_explanation": listing.recommendation_explanation,
                        "updated_at": now,
                    }
                    for listing in listings
                ],
            )

    def get_listing(self, listing_id: int) -> Listing | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
            return Listing.from_row(row) if row else None

    def search(self, query: str) -> list[Listing]:
        pattern = f"%{query.lower()}%"
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM listings
                WHERE lower(title) LIKE ?
                   OR lower(category) LIKE ?
                   OR lower(description) LIKE ?
                   OR lower(seller_notes) LIKE ?
                   OR lower(tech_stack) LIKE ?
                ORDER BY bend_score DESC, id ASC
                """,
                (pattern, pattern, pattern, pattern, pattern),
            ).fetchall()
            return [Listing.from_row(row) for row in rows]

    def top(self, limit: int = 10) -> list[Listing]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM listings ORDER BY bend_score DESC, monthly_profit DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [Listing.from_row(row) for row in rows]

    def add_to_watchlist(self, listing_id: int, status: str = "Watching") -> WatchlistItem:
        if status not in WATCHLIST_STATUSES:
            raise ValueError(f"Invalid watchlist status: {status}")
        if self.get_listing(listing_id) is None:
            raise ValueError(f"Listing #{listing_id} does not exist.")

        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO watchlist (listing_id, status, notes, date_added, date_updated)
                VALUES (?, ?, '', ?, ?)
                ON CONFLICT(listing_id) DO UPDATE SET
                    status = excluded.status,
                    date_updated = excluded.date_updated
                """,
                (listing_id, status, now, now),
            )
        item = self.get_watchlist_item(listing_id)
        if item is None:
            raise RuntimeError("Watchlist insert failed.")
        return item

    def append_note(self, listing_id: int, note: str) -> WatchlistItem:
        if self.get_watchlist_item(listing_id) is None:
            self.add_to_watchlist(listing_id)

        now = utc_now()
        stamped_note = f"[{now}] {note}"
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE watchlist
                SET notes = CASE
                        WHEN notes = '' THEN ?
                        ELSE notes || char(10) || ?
                    END,
                    date_updated = ?
                WHERE listing_id = ?
                """,
                (stamped_note, stamped_note, now, listing_id),
            )
        item = self.get_watchlist_item(listing_id)
        if item is None:
            raise RuntimeError("Watchlist note failed.")
        return item

    def get_watchlist_item(self, listing_id: int) -> WatchlistItem | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT w.*, l.id AS l_id, l.title, l.url, l.source, l.category,
                       l.asking_price, l.monthly_revenue, l.monthly_profit,
                       l.traffic_estimate, l.description, l.seller_notes,
                       l.tech_stack, l.created_at, l.updated_at, l.bend_score,
                       l.recommendation, l.recommendation_explanation
                FROM watchlist w
                JOIN listings l ON l.id = w.listing_id
                WHERE w.listing_id = ?
                """,
                (listing_id,),
            ).fetchone()
            return self._watchlist_from_row(row) if row else None

    def list_watchlist(self) -> list[WatchlistItem]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT w.*, l.id AS l_id, l.title, l.url, l.source, l.category,
                       l.asking_price, l.monthly_revenue, l.monthly_profit,
                       l.traffic_estimate, l.description, l.seller_notes,
                       l.tech_stack, l.created_at, l.updated_at, l.bend_score,
                       l.recommendation, l.recommendation_explanation
                FROM watchlist w
                JOIN listings l ON l.id = w.listing_id
                ORDER BY w.date_updated DESC
                """
            ).fetchall()
            return [self._watchlist_from_row(row) for row in rows]

    def stats(self) -> dict[str, object]:
        listings = self.list_all()
        profitable = [listing for listing in listings if listing.monthly_profit > 0]
        categories: dict[str, int] = {}
        for listing in listings:
            categories[listing.category] = categories.get(listing.category, 0) + 1

        def avg(values: list[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        multiples = [revenue_multiple(listing) for listing in profitable]
        return {
            "total": len(listings),
            "by_category": categories,
            "average_bend_score": avg([listing.bend_score or 0 for listing in listings]),
            "highest_score": max([listing.bend_score or 0 for listing in listings], default=0),
            "lowest_score": min([listing.bend_score or 0 for listing in listings], default=0),
            "average_asking_price": avg([listing.asking_price for listing in listings]),
            "average_revenue": avg([listing.monthly_revenue for listing in listings]),
            "average_profit": avg([listing.monthly_profit for listing in listings]),
            "average_revenue_multiple": avg([multiple for multiple in multiples if multiple is not None]),
        }

    def _watchlist_from_row(self, row: sqlite3.Row) -> WatchlistItem:
        listing = Listing(
            id=row["l_id"],
            title=row["title"],
            url=row["url"],
            source=row["source"],
            category=row["category"],
            asking_price=row["asking_price"],
            monthly_revenue=row["monthly_revenue"],
            monthly_profit=row["monthly_profit"],
            traffic_estimate=row["traffic_estimate"],
            description=row["description"],
            seller_notes=row["seller_notes"],
            tech_stack=row["tech_stack"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            bend_score=row["bend_score"],
            recommendation=row["recommendation"],
            recommendation_explanation=row["recommendation_explanation"],
        )
        return WatchlistItem(
            id=row["id"],
            listing_id=row["listing_id"],
            status=row["status"],
            notes=row["notes"],
            date_added=row["date_added"],
            date_updated=row["date_updated"],
            listing=listing,
        )
