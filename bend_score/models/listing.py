from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    """Return a compact UTC timestamp suitable for SQLite text columns."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Listing:
    id: int | None
    title: str
    url: str
    source: str
    category: str
    asking_price: float
    monthly_revenue: float
    monthly_profit: float
    traffic_estimate: int
    description: str
    seller_notes: str
    tech_stack: str
    created_at: str
    updated_at: str
    bend_score: float | None = None
    recommendation: str | None = None
    recommendation_explanation: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> "Listing":
        return cls(
            id=row["id"],
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
            recommendation_explanation=_row_value(row, "recommendation_explanation"),
        )


@dataclass
class WatchlistItem:
    id: int
    listing_id: int
    status: str
    notes: str
    date_added: str
    date_updated: str
    listing: Listing | None = None


def _row_value(row: Any, key: str) -> Any:
    return row[key] if key in row.keys() else None

