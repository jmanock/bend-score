from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score, combined_text, contains_any


def score(listing: Listing) -> ScorerResult:
    text = combined_text(listing)
    category = listing.category.lower()
    value = 6

    if contains_any(text, ["crowded", "ai meeting", "home office", "form-builder"]):
        value -= 2
        explanation = "Market appears competitive, so positioning needs scrutiny."
    elif contains_any(text, ["niche", "local", "wedding", "pickleball", "kayak", "bookkeepers"]):
        value += 2
        explanation = "Niche focus may reduce direct competition and improve targeting."
    elif category == "domain":
        value += 1
        explanation = "Competition is unclear, but domain-only assets keep risk contained."
    else:
        explanation = "Competitive risk appears average from the available data."

    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(63)}

