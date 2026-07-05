from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from bend_score.intake.github_opportunities import github_metadata_from_listing
from bend_score.intelligence.consensus import consensus_metadata_by_listing
from bend_score.memory import OpportunityMemory, trend_for_memory
from bend_score.models import Listing
from bend_score.scoring.bend_score import BendScoreResult, calculate_bend_score


SIGNAL_OUTBOX = Path("signals/outbox")
ALLOWED_RECOMMENDATION_TERMS = {"BUILD NOW", "ACQUIRE", "BUILD LATER", "WATCH", "RESEARCH", "BUY", "BUILD"}
BLOCKED_RECOMMENDATION_TERMS = {"IGNORE", "PASS"}


@dataclass(frozen=True)
class SignalExportSummary:
    considered: int
    exported: int
    skipped: int
    duplicates: int
    files: list[Path]

    def lines(self) -> list[str]:
        lines = [
            f"Opportunities considered: {self.considered}",
            f"Signals exported: {self.exported}",
            f"Skipped: {self.skipped}",
            f"Duplicates skipped: {self.duplicates}",
        ]
        lines.extend(f"- {path}" for path in self.files)
        return lines


def export_opportunities(
    listings: list[Listing],
    outbox_dir: Path | str = SIGNAL_OUTBOX,
    export_date: date | None = None,
    memory_records: list[OpportunityMemory] | None = None,
    consensus_metadata: dict[int, dict[str, object]] | None = None,
) -> SignalExportSummary:
    outbox = Path(outbox_dir)
    outbox.mkdir(parents=True, exist_ok=True)
    current_date = export_date or date.today()

    exported_files: list[Path] = []
    skipped = 0
    duplicates = 0
    memory_by_id = {memory.listing_id: memory for memory in (memory_records or [])}
    consensus_by_id = consensus_metadata or consensus_metadata_by_listing(listings, [], memory_records)

    for listing in listings:
        score_result = calculate_bend_score(listing)
        recommendation = _recommendation_for(listing, score_result)
        confidence = confidence_for(score_result)
        if not should_export(listing, score_result, confidence):
            skipped += 1
            continue

        path = signal_path_for(listing, outbox, current_date)
        if path.exists():
            duplicates += 1
            continue

        signal = signal_for_listing(
            listing,
            score_result,
            confidence,
            current_date,
            memory_by_id.get(listing.id),
            consensus_by_id.get(listing.id or -1),
        )
        path.write_text(json.dumps(signal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        exported_files.append(path)

    return SignalExportSummary(
        considered=len(listings),
        exported=len(exported_files),
        skipped=skipped,
        duplicates=duplicates,
        files=exported_files,
    )


def should_export(listing: Listing, score_result: BendScoreResult | None = None, confidence: int | None = None) -> bool:
    if not listing.url:
        return False
    score_result = score_result or calculate_bend_score(listing)
    recommendation = _recommendation_for(listing, score_result)
    if _contains_any(recommendation, BLOCKED_RECOMMENDATION_TERMS):
        return False
    confidence = confidence if confidence is not None else confidence_for(score_result)
    bend_score = listing.bend_score if listing.bend_score is not None else score_result.total
    return bend_score >= 70 or _contains_any(recommendation, ALLOWED_RECOMMENDATION_TERMS) or confidence >= 80


def signal_for_listing(
    listing: Listing,
    score_result: BendScoreResult | None = None,
    confidence: int | None = None,
    export_date: date | None = None,
    memory: OpportunityMemory | None = None,
    consensus_metadata: dict[str, object] | None = None,
) -> dict[str, Any]:
    score_result = score_result or calculate_bend_score(listing)
    confidence = confidence if confidence is not None else confidence_for(score_result)
    recommendation = _recommendation_for(listing, score_result)
    bend_score = listing.bend_score if listing.bend_score is not None else score_result.total
    trend = trend_for_memory(memory) if memory else None

    github_metadata = github_metadata_from_listing(listing)
    signal = {
        "source_project": "bend-score",
        "source_type": "opportunity",
        "brand": "Bend Score",
        "title": listing.title,
        "summary": _summary_for(listing, bend_score, recommendation),
        "description": listing.description or listing.recommendation_explanation or score_result.recommendation_explanation,
        "url": listing.url,
        "affiliate_url": "",
        "category": "business-opportunity",
        "priority": priority_for(bend_score, recommendation, confidence),
        "confidence": confidence,
        "tags": tags_for(listing, recommendation),
        "expiration": "",
        "image_prompt": image_prompt_for(listing),
        "metadata": {
            "original_listing_id": listing.id,
            "bend_score": bend_score,
            "founder_score": listing.founder_score,
            "portfolio_fit": listing.portfolio_fit,
            "trend": trend.label if trend else "NEW",
            "bend_score_change": trend.bend_score_change if trend else 0,
            "founder_score_change": trend.founder_score_change if trend else 0,
            "recommendation_change": trend.recommendation_change if trend else "No prior recommendation",
            "times_seen": trend.times_seen if trend else 0,
            "recommendation": recommendation,
            "build_complexity": listing.build_complexity,
            "maintenance_estimate": listing.maintenance_estimate,
            "revenue_timeline": listing.revenue_timeline,
            "executive_summary": listing.executive_summary,
            "asking_price": listing.asking_price,
            "monthly_revenue": listing.monthly_revenue,
            "monthly_profit": listing.monthly_profit,
            "source": listing.source,
            "category": listing.category,
            "score_breakdown": score_result.components,
            "recommendation_explanation": listing.recommendation_explanation or score_result.recommendation_explanation,
            "export_date": (export_date or date.today()).isoformat(),
        },
    }
    if github_metadata:
        signal["metadata"].update(
            {
                "repo_url": github_metadata.get("github_html_url") or github_metadata.get("html_url"),
                "stars": github_metadata.get("stars"),
                "forks": github_metadata.get("forks"),
                "language": github_metadata.get("language"),
                "license": github_metadata.get("license"),
                "topics": github_metadata.get("topics"),
                "reason": github_metadata.get("github_reason") or github_metadata.get("recommendation_explanation"),
                "github_founder_score": github_metadata.get("github_founder_score"),
            }
        )
    if consensus_metadata:
        signal["metadata"].update(consensus_metadata)
    return signal


def confidence_for(score_result: BendScoreResult) -> int:
    confidences = [
        int(component.get("confidence", 0))
        for component in score_result.components.values()
        if isinstance(component.get("confidence", 0), int | float)
    ]
    return max(0, min(100, round(sum(confidences) / len(confidences)))) if confidences else 70


def priority_for(bend_score: float, recommendation: str, confidence: int) -> int:
    if "BUILD NOW" in recommendation or "ACQUIRE" in recommendation or bend_score >= 85:
        return 9
    if "BUILD LATER" in recommendation or "RESEARCH" in recommendation or bend_score >= 75:
        return 8
    if "WATCH" in recommendation or confidence >= 80:
        return 7
    return 6


def tags_for(listing: Listing, recommendation: str) -> list[str]:
    tags = ["bend-score", "acquisition", "opportunity", _slug(listing.category)]
    if recommendation:
        tags.append(recommendation.lower())
    if listing.source:
        tags.append(_slug(listing.source))
    return list(dict.fromkeys(tag for tag in tags if tag))


def image_prompt_for(listing: Listing) -> str:
    return (
        f"Clean business opportunity dashboard for {listing.category}, showing revenue, profit, "
        "automation upside, and acquisition research notes."
    )


def signal_path_for(listing: Listing, outbox_dir: Path, export_date: date) -> Path:
    source = _slug(listing.source or "unknown")
    identifier = listing.id if listing.id is not None else _slug(listing.title)[:40]
    return outbox_dir / f"{export_date.isoformat()}-{source}-{identifier}.json"


def _recommendation_for(listing: Listing, score_result: BendScoreResult) -> str:
    return (listing.recommendation or score_result.recommendation or "").strip().upper()


def _summary_for(listing: Listing, bend_score: float, recommendation: str) -> str:
    category = listing.category or "business"
    descriptor = category if "opportunity" in category.lower() else f"{category} opportunity"
    return (
        f"Bend Score found a {bend_score:.0f}/100 {descriptor} "
        f"with a {recommendation or 'RESEARCH'} recommendation worth reviewing."
    )


def _contains_any(value: str, terms: set[str]) -> bool:
    normalized = value.upper()
    return any(term in normalized for term in terms)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
