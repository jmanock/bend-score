from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score, revenue_multiple


def score(listing: Listing) -> ScorerResult:
    multiple = revenue_multiple(listing)
    value = 4
    explanation = "Acquisition quality is based on price, proof of profit, and deal size."

    if multiple is not None:
        if multiple <= 12:
            value = 10
            explanation = "Revenue multiple is very attractive for a small digital asset."
        elif multiple <= 18:
            value = 8
            explanation = "Revenue multiple is attractive enough to justify diligence."
        elif multiple <= 30:
            value = 6
            explanation = "Revenue multiple is fair, but upside needs to be clear."
        else:
            value = 3
            explanation = "Price looks stretched relative to current monthly profit."
    elif listing.asking_price <= 5000:
        value = 7
        explanation = "Pre-revenue asset is cheap enough to treat as a focused experiment."
    elif listing.asking_price > 20000:
        value = 2
        explanation = "Pre-revenue price is high without profit support."

    if listing.asking_price <= 20000:
        value += 1

    confidence = 90 if listing.monthly_profit > 0 else 65
    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(confidence)}

