from __future__ import annotations

from bend_score.memory import FeedbackEntry, feedback_summary_for_listing
from bend_score.models import Listing
from bend_score.scoring.bend_score import calculate_bend_score
from bend_score.scoring.founder_score import analyze_founder_intelligence, executive_summary_for, founder_recommendation


def apply_recommendation(listing: Listing, feedback_entries: list[FeedbackEntry] | None = None) -> Listing:
    result = calculate_bend_score(listing)
    intelligence = analyze_founder_intelligence(listing, result.total)
    feedback = feedback_summary_for_listing(listing, feedback_entries or [])
    adjusted_founder_score = max(0, min(100, round(intelligence.founder_score.total + feedback.founder_adjustment, 1)))
    adjusted_portfolio_fit = max(0, min(100, round(intelligence.portfolio_fit.score + feedback.portfolio_adjustment, 1)))
    recommendation, explanation = founder_recommendation(
        result.total,
        adjusted_founder_score,
        adjusted_portfolio_fit,
        intelligence.complexity.label,
        intelligence.complexity.maintenance,
    )
    if feedback.reasons:
        explanation = f"{explanation} Feedback adjustment: {' '.join(feedback.reasons)}"
    executive_summary = executive_summary_for(
        listing,
        recommendation,
        adjusted_founder_score,
        adjusted_portfolio_fit,
        intelligence.complexity.label,
        intelligence.revenue_timeline.label,
    )
    listing.bend_score = result.total
    listing.founder_score = adjusted_founder_score
    reasons = list(intelligence.founder_score.reasons)
    reasons.extend(feedback.reasons)
    listing.founder_reasons = "\n".join(dict.fromkeys(reasons))
    listing.portfolio_fit = adjusted_portfolio_fit
    listing.build_complexity = intelligence.complexity.label
    listing.build_complexity_explanation = intelligence.complexity.explanation
    listing.maintenance_estimate = intelligence.complexity.maintenance
    listing.revenue_timeline = intelligence.revenue_timeline.label
    listing.revenue_timeline_explanation = intelligence.revenue_timeline.explanation
    listing.executive_summary = executive_summary
    listing.recommendation = recommendation
    listing.recommendation_explanation = explanation
    return listing
