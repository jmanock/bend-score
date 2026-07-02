from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score


def score(listing: Listing) -> ScorerResult:
    category = listing.category.lower()
    value = 4

    if listing.monthly_profit >= 1000:
        value += 3
    elif listing.monthly_profit >= 300:
        value += 2
    elif listing.monthly_profit > 0:
        value += 1

    if category in {"saas", "content site", "affiliate site", "wordpress plugin"}:
        value += 2
        explanation = "Category has a clear buyer universe if metrics improve."
    elif category in {"newsletter", "mobile app", "chrome extension"}:
        value += 1
        explanation = "Exit path exists, but buyer pool may be more specialized."
    else:
        explanation = "Exit path depends on validation and positioning."

    confidence = 78 if listing.monthly_profit > 0 else 55
    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(confidence)}

