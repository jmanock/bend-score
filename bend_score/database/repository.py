from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from bend_score.config import DATABASE_PATH
from bend_score.memory import FeedbackEntry, OpportunityMemory, ScoreSnapshot
from bend_score.models import Listing, Signal, WatchlistItem, utc_now
from bend_score.scoring.common import revenue_multiple


DEFAULT_DB_PATH = DATABASE_PATH
WATCHLIST_STATUSES = {"Watching", "Researching", "Interested", "Contacted", "Passed", "Purchased"}


class ListingRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
                    founder_score REAL,
                    founder_reasons TEXT,
                    portfolio_fit REAL,
                    build_complexity TEXT,
                    build_complexity_explanation TEXT,
                    maintenance_estimate TEXT,
                    revenue_timeline TEXT,
                    revenue_timeline_explanation TEXT,
                    executive_summary TEXT,
                    recommendation TEXT,
                    recommendation_explanation TEXT
                )
                """
            )
            self._add_column_if_missing(connection, "listings", "founder_score", "REAL")
            self._add_column_if_missing(connection, "listings", "founder_reasons", "TEXT")
            self._add_column_if_missing(connection, "listings", "portfolio_fit", "REAL")
            self._add_column_if_missing(connection, "listings", "build_complexity", "TEXT")
            self._add_column_if_missing(connection, "listings", "build_complexity_explanation", "TEXT")
            self._add_column_if_missing(connection, "listings", "maintenance_estimate", "TEXT")
            self._add_column_if_missing(connection, "listings", "revenue_timeline", "TEXT")
            self._add_column_if_missing(connection, "listings", "revenue_timeline_explanation", "TEXT")
            self._add_column_if_missing(connection, "listings", "executive_summary", "TEXT")
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    observer TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    confidence INTEGER NOT NULL,
                    impact TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    observer TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    confidence INTEGER NOT NULL,
                    impact TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_memory (
                    listing_id INTEGER PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    current_bend_score REAL NOT NULL DEFAULT 0,
                    current_founder_score REAL NOT NULL DEFAULT 0,
                    current_recommendation TEXT NOT NULL DEFAULT '',
                    times_seen INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_score_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    bend_score REAL NOT NULL DEFAULT 0,
                    founder_score REAL NOT NULL DEFAULT 0,
                    recommendation TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER NOT NULL,
                    reaction TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
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

    def insert_signals(self, signals: Iterable[Signal]) -> list[Signal]:
        inserted: list[Signal] = []
        with self.connect() as connection:
            for signal in signals:
                if self._is_duplicate_same_day_signal(connection, signal):
                    continue
                cursor = connection.execute(
                    """
                    INSERT INTO signals (
                        timestamp, observer, signal_type, title, description,
                        category, confidence, impact, recommendation, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.timestamp,
                        signal.observer,
                        signal.signal_type,
                        signal.title,
                        signal.description,
                        signal.category,
                        signal.confidence,
                        signal.impact,
                        signal.recommendation,
                        signal.metadata_json(),
                    ),
                )
                signal.id = cursor.lastrowid
                connection.execute(
                    """
                    INSERT INTO signal_history (
                        signal_id, timestamp, observer, signal_type, title,
                        confidence, impact, recommendation, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.id,
                        signal.timestamp,
                        signal.observer,
                        signal.signal_type,
                        signal.title,
                        signal.confidence,
                        signal.impact,
                        signal.recommendation,
                        signal.metadata_json(),
                    ),
                )
                inserted.append(signal)
        return inserted

    def list_signals(self, limit: int = 100, observer: str | None = None) -> list[Signal]:
        with self.connect() as connection:
            if observer:
                rows = connection.execute(
                    "SELECT * FROM signals WHERE observer = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
                    (observer, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM signals ORDER BY timestamp DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [Signal.from_row(row) for row in rows]

    def _is_duplicate_same_day_signal(self, connection: sqlite3.Connection, signal: Signal) -> bool:
        full_name = signal.metadata.get("github_full_name")
        signal_type = signal.metadata.get("github_signal_type")
        if not full_name or not signal_type:
            return False
        day = signal.timestamp[:10]
        rows = connection.execute(
            """
            SELECT metadata
            FROM signals
            WHERE observer = ?
              AND signal_type = ?
              AND substr(timestamp, 1, 10) = ?
            """,
            (signal.observer, signal.signal_type, day),
        ).fetchall()
        for row in rows:
            try:
                metadata = json.loads(row["metadata"] or "{}")
            except json.JSONDecodeError:
                continue
            if (
                metadata.get("github_full_name") == full_name
                and metadata.get("github_signal_type") == signal_type
            ):
                return True
        return False

    def signal_stats(self) -> dict[str, object]:
        with self.connect() as connection:
            total = connection.execute("SELECT COUNT(*) AS count FROM signals").fetchone()["count"]
            history_total = connection.execute("SELECT COUNT(*) AS count FROM signal_history").fetchone()["count"]
            avg_confidence = connection.execute(
                "SELECT AVG(confidence) AS average FROM signals"
            ).fetchone()["average"]
            highest_confidence = connection.execute(
                "SELECT MAX(confidence) AS highest FROM signals"
            ).fetchone()["highest"]
            by_observer = {
                row["observer"]: row["count"]
                for row in connection.execute(
                    "SELECT observer, COUNT(*) AS count FROM signals GROUP BY observer ORDER BY observer"
                ).fetchall()
            }
            return {
                "signals": total,
                "history": history_total,
                "average_confidence": float(avg_confidence or 0),
                "highest_confidence": int(highest_confidence or 0),
                "by_observer": by_observer,
            }

    def add_many(self, listings: Iterable[Listing]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO listings (
                    title, url, source, category, asking_price, monthly_revenue,
                    monthly_profit, traffic_estimate, description, seller_notes,
                    tech_stack, created_at, updated_at, bend_score, founder_score,
                    founder_reasons, portfolio_fit, build_complexity,
                    build_complexity_explanation, maintenance_estimate,
                    revenue_timeline, revenue_timeline_explanation, executive_summary,
                    recommendation, recommendation_explanation
                )
                VALUES (
                    :title, :url, :source, :category, :asking_price, :monthly_revenue,
                    :monthly_profit, :traffic_estimate, :description, :seller_notes,
                    :tech_stack, :created_at, :updated_at, :bend_score, :founder_score,
                    :founder_reasons, :portfolio_fit, :build_complexity,
                    :build_complexity_explanation, :maintenance_estimate,
                    :revenue_timeline, :revenue_timeline_explanation, :executive_summary,
                    :recommendation, :recommendation_explanation
                )
                """,
                [listing.__dict__ for listing in listings],
            )

    def add_listing(self, listing: Listing) -> Listing:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO listings (
                    title, url, source, category, asking_price, monthly_revenue,
                    monthly_profit, traffic_estimate, description, seller_notes,
                    tech_stack, created_at, updated_at, bend_score, founder_score,
                    founder_reasons, portfolio_fit, build_complexity,
                    build_complexity_explanation, maintenance_estimate,
                    revenue_timeline, revenue_timeline_explanation, executive_summary,
                    recommendation,
                    recommendation_explanation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing.title,
                    listing.url,
                    listing.source,
                    listing.category,
                    listing.asking_price,
                    listing.monthly_revenue,
                    listing.monthly_profit,
                    listing.traffic_estimate,
                    listing.description,
                    listing.seller_notes,
                    listing.tech_stack,
                    listing.created_at,
                    listing.updated_at,
                    listing.bend_score,
                    listing.founder_score,
                    listing.founder_reasons,
                    listing.portfolio_fit,
                    listing.build_complexity,
                    listing.build_complexity_explanation,
                    listing.maintenance_estimate,
                    listing.revenue_timeline,
                    listing.revenue_timeline_explanation,
                    listing.executive_summary,
                    listing.recommendation,
                    listing.recommendation_explanation,
                ),
            )
            listing.id = cursor.lastrowid
        return listing

    def is_duplicate_listing(self, listing: Listing) -> bool:
        title = listing.title.strip().lower()
        url = listing.url.strip().lower()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM listings
                WHERE lower(trim(title)) = ?
                  AND lower(trim(url)) = ?
                LIMIT 1
                """,
                (title, url),
            ).fetchone()
            return row is not None

    def list_all(self) -> list[Listing]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM listings ORDER BY id").fetchall()
            return [Listing.from_row(row) for row in rows]

    def recent_listings(self, limit: int = 25) -> list[Listing]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM listings ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [Listing.from_row(row) for row in rows]

    def update_scores(self, listings: Iterable[Listing]) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.executemany(
                """
                UPDATE listings
                SET bend_score = :bend_score,
                    founder_score = :founder_score,
                    founder_reasons = :founder_reasons,
                    portfolio_fit = :portfolio_fit,
                    build_complexity = :build_complexity,
                    build_complexity_explanation = :build_complexity_explanation,
                    maintenance_estimate = :maintenance_estimate,
                    revenue_timeline = :revenue_timeline,
                    revenue_timeline_explanation = :revenue_timeline_explanation,
                    executive_summary = :executive_summary,
                    recommendation = :recommendation,
                    recommendation_explanation = :recommendation_explanation,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                [
                    {
                        "id": listing.id,
                        "bend_score": listing.bend_score,
                        "founder_score": listing.founder_score,
                        "founder_reasons": listing.founder_reasons,
                        "portfolio_fit": listing.portfolio_fit,
                        "build_complexity": listing.build_complexity,
                        "build_complexity_explanation": listing.build_complexity_explanation,
                        "maintenance_estimate": listing.maintenance_estimate,
                        "revenue_timeline": listing.revenue_timeline,
                        "revenue_timeline_explanation": listing.revenue_timeline_explanation,
                        "executive_summary": listing.executive_summary,
                        "recommendation": listing.recommendation,
                        "recommendation_explanation": listing.recommendation_explanation,
                        "updated_at": now,
                    }
                    for listing in listings
                ],
            )

    def record_opportunity_memory(self, listings: Iterable[Listing]) -> list[OpportunityMemory]:
        now = utc_now()
        listing_list = [listing for listing in listings if listing.id is not None]
        with self.connect() as connection:
            for listing in listing_list:
                existing = connection.execute(
                    "SELECT listing_id FROM opportunity_memory WHERE listing_id = ?",
                    (listing.id,),
                ).fetchone()
                if existing:
                    connection.execute(
                        """
                        UPDATE opportunity_memory
                        SET last_seen = ?,
                            title = ?,
                            category = ?,
                            source = ?,
                            current_bend_score = ?,
                            current_founder_score = ?,
                            current_recommendation = ?,
                            times_seen = times_seen + 1
                        WHERE listing_id = ?
                        """,
                        (
                            now,
                            listing.title,
                            listing.category,
                            listing.source,
                            listing.bend_score or 0,
                            listing.founder_score or 0,
                            listing.recommendation or "",
                            listing.id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO opportunity_memory (
                            listing_id, first_seen, last_seen, title, category, source,
                            current_bend_score, current_founder_score, current_recommendation,
                            times_seen, notes
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '')
                        """,
                        (
                            listing.id,
                            now,
                            now,
                            listing.title,
                            listing.category,
                            listing.source,
                            listing.bend_score or 0,
                            listing.founder_score or 0,
                            listing.recommendation or "",
                        ),
                    )
                connection.execute(
                    """
                    INSERT INTO opportunity_score_history (
                        listing_id, timestamp, bend_score, founder_score, recommendation
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        listing.id,
                        now,
                        listing.bend_score or 0,
                        listing.founder_score or 0,
                        listing.recommendation or "",
                    ),
                )
        return self.list_opportunity_memory()

    def list_opportunity_memory(self) -> list[OpportunityMemory]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM opportunity_memory ORDER BY current_founder_score DESC, current_bend_score DESC"
            ).fetchall()
            history_rows = connection.execute(
                "SELECT * FROM opportunity_score_history ORDER BY timestamp ASC, id ASC"
            ).fetchall()
        history_by_listing: dict[int, list[ScoreSnapshot]] = {}
        for row in history_rows:
            history_by_listing.setdefault(row["listing_id"], []).append(
                ScoreSnapshot(
                    timestamp=row["timestamp"],
                    bend_score=float(row["bend_score"]),
                    founder_score=float(row["founder_score"]),
                    recommendation=row["recommendation"],
                )
            )
        return [
            OpportunityMemory(
                listing_id=row["listing_id"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                title=row["title"],
                category=row["category"],
                source=row["source"],
                current_bend_score=float(row["current_bend_score"]),
                current_founder_score=float(row["current_founder_score"]),
                current_recommendation=row["current_recommendation"],
                times_seen=int(row["times_seen"]),
                notes=row["notes"],
                history=history_by_listing.get(row["listing_id"], []),
            )
            for row in rows
        ]

    def get_opportunity_memory(self, listing_id: int) -> OpportunityMemory | None:
        for memory in self.list_opportunity_memory():
            if memory.listing_id == listing_id:
                return memory
        return None

    def add_feedback(self, listing_id: int, reaction: str, note: str = "") -> FeedbackEntry:
        listing = self.get_listing(listing_id)
        if listing is None:
            raise ValueError(f"Listing #{listing_id} does not exist.")
        now = utc_now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO opportunity_feedback (listing_id, reaction, note, category, title, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (listing_id, reaction, note, listing.category, listing.title, now),
            )
        return FeedbackEntry(
            id=cursor.lastrowid,
            listing_id=listing_id,
            reaction=reaction,
            note=note,
            category=listing.category,
            title=listing.title,
            created_at=now,
        )

    def list_feedback(self, listing_id: int | None = None, limit: int = 200) -> list[FeedbackEntry]:
        with self.connect() as connection:
            if listing_id is None:
                rows = connection.execute(
                    "SELECT * FROM opportunity_feedback ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM opportunity_feedback WHERE listing_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                    (listing_id, limit),
                ).fetchall()
        return [
            FeedbackEntry(
                id=row["id"],
                listing_id=row["listing_id"],
                reaction=row["reaction"],
                note=row["note"],
                category=row["category"],
                title=row["title"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

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
                       l.founder_score, l.founder_reasons, l.portfolio_fit,
                       l.build_complexity, l.build_complexity_explanation,
                       l.maintenance_estimate, l.revenue_timeline,
                       l.revenue_timeline_explanation, l.executive_summary,
                       l.recommendation, l.recommendation_explanation
                FROM watchlist w
                JOIN listings l ON l.id = w.listing_id
                WHERE w.listing_id = ?
                """,
                (listing_id,),
            ).fetchone()
            return self._watchlist_from_row(row) if row else None

    def watchlist_status(self, listing_id: int) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status FROM watchlist WHERE listing_id = ?",
                (listing_id,),
            ).fetchone()
            return row["status"] if row else None

    def list_watchlist(self) -> list[WatchlistItem]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT w.*, l.id AS l_id, l.title, l.url, l.source, l.category,
                       l.asking_price, l.monthly_revenue, l.monthly_profit,
                       l.traffic_estimate, l.description, l.seller_notes,
                       l.tech_stack, l.created_at, l.updated_at, l.bend_score,
                       l.founder_score, l.founder_reasons, l.portfolio_fit,
                       l.build_complexity, l.build_complexity_explanation,
                       l.maintenance_estimate, l.revenue_timeline,
                       l.revenue_timeline_explanation, l.executive_summary,
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
            "average_founder_score": avg([listing.founder_score or 0 for listing in listings]),
            "average_portfolio_fit": avg([listing.portfolio_fit or 0 for listing in listings]),
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
            founder_score=row["founder_score"],
            founder_reasons=row["founder_reasons"],
            portfolio_fit=row["portfolio_fit"],
            build_complexity=row["build_complexity"],
            build_complexity_explanation=row["build_complexity_explanation"],
            maintenance_estimate=row["maintenance_estimate"],
            revenue_timeline=row["revenue_timeline"],
            revenue_timeline_explanation=row["revenue_timeline_explanation"],
            executive_summary=row["executive_summary"],
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
