from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score, combined_text, contains_any


def score(listing: Listing) -> ScorerResult:
    text = combined_text(listing)
    category = listing.category.lower()
    value = 3
    reasons = []

    if category in {"content site", "affiliate site", "newsletter", "domain"}:
        value += 3
        reasons.append("category is naturally organic-search friendly")
    if listing.traffic_estimate >= 10000:
        value += 2
        reasons.append("existing traffic gives SEO work a base to compound")
    if contains_any(text, ["thin", "local", "directory", "comparison", "informational", "parked", "city pages"]):
        value += 2
        reasons.append("content structure suggests expansion opportunities")

    explanation = "SEO opportunity is modest based on the current category and traffic."
    if reasons:
        explanation = "SEO upside: " + "; ".join(reasons) + "."

    confidence = 82 if listing.traffic_estimate > 0 else 55
    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(confidence)}

