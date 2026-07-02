from __future__ import annotations

from typing import TypedDict

from bend_score.models import Listing


class ScorerResult(TypedDict):
    score: int
    explanation: str
    confidence: int


def clamp_score(score: int | float) -> int:
    return max(0, min(10, int(round(score))))


def clamp_confidence(confidence: int | float) -> int:
    return max(0, min(100, int(round(confidence))))


def combined_text(listing: Listing) -> str:
    return f"{listing.title} {listing.description} {listing.seller_notes} {listing.tech_stack}".lower()


def contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def revenue_multiple(listing: Listing) -> float | None:
    if listing.monthly_profit <= 0:
        return None
    return listing.asking_price / listing.monthly_profit

