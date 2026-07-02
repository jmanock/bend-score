from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score, combined_text, contains_any


def score(listing: Listing) -> ScorerResult:
    text = combined_text(listing)
    category = listing.category.lower()
    value = 4
    reasons = []

    if category in {"saas", "newsletter", "mobile app", "wordpress plugin", "chrome extension"}:
        value += 2
        reasons.append("product workflow can likely benefit from automated onboarding or retention")
    if contains_any(text, ["manual", "lifecycle", "email", "support", "docs", "inconsistent", "integrations", "onboarding"]):
        value += 3
        reasons.append("seller notes point to repeatable operating gaps")
    if listing.monthly_revenue > 0:
        value += 1
        reasons.append("existing customers make automation leverage more valuable")

    explanation = "Automation upside is limited from the available listing data."
    if reasons:
        explanation = "Automation upside: " + "; ".join(reasons) + "."

    confidence = 78 if reasons else 58
    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(confidence)}

