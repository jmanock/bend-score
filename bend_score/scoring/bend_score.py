from __future__ import annotations

from dataclasses import dataclass

from bend_score.config import DEFAULT_SCORING_WEIGHTS
from bend_score.models import Listing
from bend_score.scoring import (
    acquisition_score,
    ai_leverage_score,
    automation_score,
    competition_score,
    exit_score,
    maintenance_score,
    revenue_score,
    seo_score,
)
from bend_score.scoring.common import ScorerResult


SCORERS = {
    "acquisition": acquisition_score.score,
    "automation": automation_score.score,
    "seo": seo_score.score,
    "revenue": revenue_score.score,
    "maintenance": maintenance_score.score,
    "ai_leverage": ai_leverage_score.score,
    "competition": competition_score.score,
    "exit": exit_score.score,
}


@dataclass(frozen=True)
class BendScoreResult:
    total: float
    recommendation: str
    recommendation_explanation: str
    components: dict[str, ScorerResult]


def calculate_bend_score(listing: Listing) -> BendScoreResult:
    components = {name: scorer(listing) for name, scorer in SCORERS.items()}
    weighted_total = 0.0
    total_weight = 0.0

    for name, result in components.items():
        weight = DEFAULT_SCORING_WEIGHTS[name]
        weighted_total += result["score"] * weight
        total_weight += weight

    total = round((weighted_total / total_weight) * 10, 1)
    recommendation, explanation = recommendation_for(total, components)
    return BendScoreResult(total, recommendation, explanation, components)


def recommendation_for(total: float, components: dict[str, ScorerResult] | None = None) -> tuple[str, str]:
    components = components or {}
    acquisition = components.get("acquisition", {}).get("score", 0)
    revenue = components.get("revenue", {}).get("score", 0)
    seo = components.get("seo", {}).get("score", 0)
    automation = components.get("automation", {}).get("score", 0)

    if total >= 78 and acquisition >= 7 and revenue >= 5:
        return "BUY", "Strong overall score with attractive acquisition and revenue signals."
    if total >= 68 and (seo >= 8 or automation >= 8 or revenue >= 7):
        return "RESEARCH", "Promising upside signal deserves deeper diligence before action."
    if total >= 55:
        return "WATCH", "Some useful signals, but the opportunity needs more proof or a better price."
    return "IGNORE", "Current signals are too weak for serious acquisition work."
