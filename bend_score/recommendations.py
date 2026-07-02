from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.bend_score import calculate_bend_score


def apply_recommendation(listing: Listing) -> Listing:
    result = calculate_bend_score(listing)
    listing.bend_score = result.total
    listing.recommendation = result.recommendation
    listing.recommendation_explanation = result.recommendation_explanation
    return listing

