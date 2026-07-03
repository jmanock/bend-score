from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from bend_score.models import Listing, utc_now
from bend_score.recommendations import apply_recommendation
from bend_score.intake.validation import normalize_source, parse_int, parse_number, validate_url


CSV_COLUMNS = {
    "title",
    "url",
    "source",
    "category",
    "asking_price",
    "monthly_revenue",
    "monthly_profit",
    "traffic_estimate",
    "description",
    "seller_notes",
    "tech_stack",
}


@dataclass
class ImportResult:
    rows_processed: int = 0
    imported: list[Listing] = field(default_factory=list)
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def highest_scoring(self) -> Listing | None:
        if not self.imported:
            return None
        return max(self.imported, key=lambda listing: listing.bend_score or 0)


def listing_from_mapping(data: dict[str, object]) -> Listing:
    now = utc_now()
    title = str(data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required.")

    listing = Listing(
        id=None,
        title=title,
        url=validate_url(str(data.get("url") or "")),
        source=normalize_source(str(data.get("source") or "")),
        category=str(data.get("category") or "Other").strip() or "Other",
        asking_price=parse_number(data.get("asking_price"), "asking_price"),
        monthly_revenue=parse_number(data.get("monthly_revenue"), "monthly_revenue"),
        monthly_profit=parse_number(data.get("monthly_profit"), "monthly_profit"),
        traffic_estimate=parse_int(data.get("traffic_estimate"), "traffic_estimate"),
        description=str(data.get("description") or "").strip(),
        seller_notes=str(data.get("seller_notes") or data.get("notes") or "").strip(),
        tech_stack=str(data.get("tech_stack") or "").strip(),
        created_at=now,
        updated_at=now,
    )
    return apply_recommendation(listing)


def load_csv_rows(path: Path) -> Iterable[dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield {key: value for key, value in row.items() if key in CSV_COLUMNS}
