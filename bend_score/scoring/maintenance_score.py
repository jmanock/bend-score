from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import ScorerResult, clamp_confidence, clamp_score, combined_text, contains_any


def score(listing: Listing) -> ScorerResult:
    text = combined_text(listing)
    stack = listing.tech_stack.lower()
    value = 5

    if contains_any(stack, ["wordpress", "webflow", "beehiiv", "domain only", "airtable"]):
        value += 3
        explanation = "Stack looks simple enough for a lean operator."
    elif contains_any(stack, ["django", "rails", "laravel", "firebase", "javascript", "php", "swift", "kotlin"]):
        value += 1
        explanation = "Stack is maintainable, but needs product/engineering comfort."
    else:
        explanation = "Maintenance burden is unclear from the listing."

    if contains_any(text, ["support volume is low", "low churn", "minimal marketing"]):
        value += 1
    if contains_any(text, ["clunky", "outdated", "bare", "weak", "docs are weak"]):
        value -= 1

    return {"score": clamp_score(value), "explanation": explanation, "confidence": clamp_confidence(74)}

