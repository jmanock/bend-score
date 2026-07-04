from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from bend_score.models import Listing
from bend_score.scoring.bend_score import BendScoreResult, calculate_bend_score


SIGNAL_OUTBOX = Path("signals/outbox")
ALLOWED_RECOMMENDATIONS = {"BUY", "BUILD", "WATCH", "RESEARCH"}
BLOCKED_RECOMMENDATIONS = {"IGNORE", "PASS"}


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
) -> SignalExportSummary:
    outbox = Path(outbox_dir)
    outbox.mkdir(parents=True, exist_ok=True)
    current_date = export_date or date.today()

    exported_files: list[Path] = []
    skipped = 0
    duplicates = 0

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

        signal = signal_for_listing(listing, score_result, confidence, current_date)
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
    if recommendation in BLOCKED_RECOMMENDATIONS:
        return False
    confidence = confidence if confidence is not None else confidence_for(score_result)
    bend_score = listing.bend_score if listing.bend_score is not None else score_result.total
    return bend_score >= 70 or recommendation in ALLOWED_RECOMMENDATIONS or confidence >= 80


def signal_for_listing(
    listing: Listing,
    score_result: BendScoreResult | None = None,
    confidence: int | None = None,
    export_date: date | None = None,
) -> dict[str, Any]:
    score_result = score_result or calculate_bend_score(listing)
    confidence = confidence if confidence is not None else confidence_for(score_result)
    recommendation = _recommendation_for(listing, score_result)
    bend_score = listing.bend_score if listing.bend_score is not None else score_result.total

    return {
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
            "recommendation": recommendation,
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


def confidence_for(score_result: BendScoreResult) -> int:
    confidences = [
        int(component.get("confidence", 0))
        for component in score_result.components.values()
        if isinstance(component.get("confidence", 0), int | float)
    ]
    return max(0, min(100, round(sum(confidences) / len(confidences)))) if confidences else 70


def priority_for(bend_score: float, recommendation: str, confidence: int) -> int:
    if recommendation == "BUY" or bend_score >= 85:
        return 9
    if recommendation in {"BUILD", "RESEARCH"} or bend_score >= 75:
        return 8
    if recommendation == "WATCH" or confidence >= 80:
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
    return (
        f"Bend Score found a {bend_score:.0f}/100 {listing.category} opportunity "
        f"with a {recommendation or 'RESEARCH'} recommendation worth reviewing."
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
