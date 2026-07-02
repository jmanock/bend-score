from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score, combined_text, contains_any


def score(listing: Listing) -> ScorerResult:
    text = combined_text(listing)
    category = listing.category.lower()
    value = 4
    reasons = []

    if category in {"content site", "affiliate site", "newsletter", "saas"}:
        value += 2
        reasons.append("category can use AI for content, research, support, or onboarding")
    if contains_any(text, ["directory", "templates", "curated", "comparison", "docs", "support", "data"]):
        value += 3
        reasons.append("asset contains repeatable information workflows")
    if listing.traffic_estimate > 5000:
        value += 1
        reasons.append("existing audience makes AI-assisted iteration easier to test")

    explanation = "AI leverage is possible but not obvious from the listing."
    if reasons:
        explanation = "AI leverage: " + "; ".join(reasons) + "."

    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(70 if reasons else 52)}

