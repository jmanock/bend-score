from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score


def score(listing: Listing) -> ScorerResult:
    revenue = listing.monthly_revenue
    value = 1

    if revenue >= 2500:
        value = 10
    elif revenue >= 1500:
        value = 8
    elif revenue >= 750:
        value = 7
    elif revenue >= 300:
        value = 5
    elif revenue > 0:
        value = 3

    if listing.traffic_estimate > 5000 and revenue < 500:
        value += 2
        explanation = "Traffic is meaningful, but revenue appears under-monetized."
    elif revenue > 0:
        explanation = "Business has existing revenue proof."
    else:
        explanation = "No current revenue signal; upside depends on validation."

    confidence = 88 if revenue > 0 else 62
    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(confidence)}

