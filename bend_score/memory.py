from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bend_score.config import REPORT_DIR
from bend_score.models import Listing
from bend_score.scoring.bend_score import calculate_bend_score


HISTORY_EXPORT_DIR = REPORT_DIR / "opportunity_history"


@dataclass(frozen=True)
class ScoreSnapshot:
    timestamp: str
    bend_score: float
    founder_score: float
    recommendation: str


@dataclass(frozen=True)
class OpportunityMemory:
    listing_id: int
    first_seen: str
    last_seen: str
    title: str
    category: str
    source: str
    current_bend_score: float
    current_founder_score: float
    current_recommendation: str
    times_seen: int
    notes: str
    history: list[ScoreSnapshot]

    @property
    def historical_bend_scores(self) -> list[float]:
        return [snapshot.bend_score for snapshot in self.history]

    @property
    def historical_founder_scores(self) -> list[float]:
        return [snapshot.founder_score for snapshot in self.history]

    @property
    def recommendation_history(self) -> list[str]:
        return [snapshot.recommendation for snapshot in self.history]


@dataclass(frozen=True)
class Trend:
    label: str
    bend_score_change: float
    founder_score_change: float
    recommendation_change: str
    times_seen: int


@dataclass(frozen=True)
class FeedbackEntry:
    id: int | None
    listing_id: int
    reaction: str
    note: str
    category: str
    title: str
    created_at: str


@dataclass(frozen=True)
class FeedbackSummary:
    founder_adjustment: float
    portfolio_adjustment: float
    reasons: list[str]


@dataclass(frozen=True)
class OpportunityCluster:
    name: str
    reason: str
    listings: list[Listing]


@dataclass(frozen=True)
class RoadmapItem:
    listing: Listing
    action: str
    next_action: str
    score: float
    estimated_mvp_timeline: str


@dataclass(frozen=True)
class Movers:
    biggest_rising: OpportunityMemory | None
    biggest_falling: OpportunityMemory | None
    newly_discovered: list[OpportunityMemory]
    most_consistent: OpportunityMemory | None
    most_volatile: OpportunityMemory | None


def trend_for_memory(memory: OpportunityMemory) -> Trend:
    history = memory.history
    if len(history) <= 1:
        return Trend("NEW", 0.0, 0.0, "No prior recommendation", memory.times_seen)

    first = history[0]
    latest = history[-1]
    bend_change = round(latest.bend_score - first.bend_score, 1)
    founder_change = round(latest.founder_score - first.founder_score, 1)
    recommendation_change = (
        "No change" if first.recommendation == latest.recommendation else f"{first.recommendation} -> {latest.recommendation}"
    )
    founder_values = [snapshot.founder_score for snapshot in history[-5:]]
    bend_values = [snapshot.bend_score for snapshot in history[-5:]]
    volatility = _range(founder_values) + _range(bend_values)
    combined_change = founder_change + bend_change

    if volatility >= 18 and len(history) >= 3:
        label = "VOLATILE"
    elif combined_change >= 4:
        label = "RISING"
    elif combined_change <= -4:
        label = "FALLING"
    else:
        label = "STABLE"

    return Trend(label, bend_change, founder_change, recommendation_change, memory.times_seen)


def movers_for(memory_records: list[OpportunityMemory]) -> Movers:
    if not memory_records:
        return Movers(None, None, [], None, None)

    def combined_delta(memory: OpportunityMemory) -> float:
        trend = trend_for_memory(memory)
        return trend.bend_score_change + trend.founder_score_change

    with_history = [memory for memory in memory_records if len(memory.history) > 1]
    rising = max(with_history, key=combined_delta, default=None)
    falling = min(with_history, key=combined_delta, default=None)
    new_high = sorted(
        [
            memory
            for memory in memory_records
            if trend_for_memory(memory).label == "NEW" and memory.current_founder_score >= 72
        ],
        key=lambda memory: memory.current_founder_score,
        reverse=True,
    )[:3]
    consistent = min(
        [memory for memory in memory_records if len(memory.history) >= 2],
        key=lambda memory: _range(memory.historical_founder_scores[-5:]) + _range(memory.historical_bend_scores[-5:]),
        default=None,
    )
    volatile = max(
        [memory for memory in memory_records if len(memory.history) >= 2],
        key=lambda memory: _range(memory.historical_founder_scores[-5:]) + _range(memory.historical_bend_scores[-5:]),
        default=None,
    )
    return Movers(rising, falling, new_high, consistent, volatile)


def feedback_summary_for_listing(listing: Listing, feedback_entries: list[FeedbackEntry]) -> FeedbackSummary:
    category = listing.category.lower()
    matching = [entry for entry in feedback_entries if entry.category.lower() == category or entry.listing_id == listing.id]
    founder_adjustment = 0.0
    portfolio_adjustment = 0.0
    reasons: list[str] = []

    for entry in matching[-8:]:
        reaction = entry.reaction.lower()
        same_listing = entry.listing_id == listing.id
        scale = 1.0 if same_listing else 0.5
        if reaction == "love":
            founder_adjustment += 2.0 * scale
            portfolio_adjustment += 1.5 * scale
            reasons.append(f"Founder feedback loved {entry.category}.")
        elif reaction == "like":
            founder_adjustment += 1.0 * scale
            reasons.append(f"Founder feedback liked {entry.category}.")
        elif reaction == "build":
            founder_adjustment += 1.5 * scale
            portfolio_adjustment += 2.0 * scale
            reasons.append(f"Build reaction increases portfolio-fit confidence for {entry.category}.")
        elif reaction == "buy":
            portfolio_adjustment += 2.0 * scale
            reasons.append(f"Buy reaction increases acquisition interest for {entry.category}.")
        elif reaction in {"ignore", "pass"}:
            founder_adjustment -= 1.5 * scale
            if "high" in (listing.maintenance_estimate or "").lower():
                founder_adjustment -= 1.0 * scale
            reasons.append(f"Founder feedback cooled on {entry.category}.")
        elif reaction == "research":
            founder_adjustment += 0.5 * scale
            reasons.append(f"Research reaction keeps {entry.category} in consideration.")

    return FeedbackSummary(
        founder_adjustment=max(-5.0, min(5.0, round(founder_adjustment, 1))),
        portfolio_adjustment=max(-4.0, min(4.0, round(portfolio_adjustment, 1))),
        reasons=list(dict.fromkeys(reasons))[:3],
    )


def detect_clusters(listings: list[Listing], limit: int = 5) -> list[OpportunityCluster]:
    groups: dict[str, list[Listing]] = {}
    for listing in listings:
        for key in _cluster_keys(listing):
            groups.setdefault(key, []).append(listing)

    clusters: list[OpportunityCluster] = []
    seen_sets: set[tuple[int, ...]] = set()
    for key, members in groups.items():
        unique_members = sorted({member.id: member for member in members if member.id is not None}.values(), key=lambda item: item.title)
        if len(unique_members) < 2:
            continue
        member_key = tuple(sorted(member.id or 0 for member in unique_members))
        if member_key in seen_sets:
            continue
        seen_sets.add(member_key)
        clusters.append(
            OpportunityCluster(
                name=_cluster_name(key, unique_members),
                reason=_cluster_reason(key, unique_members),
                listings=unique_members[:5],
            )
        )

    return sorted(clusters, key=lambda cluster: (len(cluster.listings), _average_founder(cluster.listings)), reverse=True)[:limit]


def build_roadmap(
    listings: list[Listing],
    memory_records: list[OpportunityMemory],
    feedback_entries: list[FeedbackEntry],
    limit: int = 5,
) -> list[RoadmapItem]:
    memory_by_id = {memory.listing_id: memory for memory in memory_records}
    roadmap: list[RoadmapItem] = []
    for listing in listings:
        feedback = feedback_summary_for_listing(listing, feedback_entries)
        component = calculate_bend_score(listing).components
        seo = component.get("seo", {}).get("score", 0) * 10
        automation = component.get("automation", {}).get("score", 0) * 10
        maintenance_bonus = 12 if "low" in (listing.maintenance_estimate or "").lower() else 4
        history_bonus = min(8, (memory_by_id.get(listing.id).times_seen if listing.id in memory_by_id else 0))
        score = (
            (listing.founder_score or 0) * 0.34
            + (listing.portfolio_fit or 0) * 0.24
            + seo * 0.14
            + automation * 0.14
            + maintenance_bonus
            + history_bonus
            + feedback.founder_adjustment
            + feedback.portfolio_adjustment
        )
        action = _roadmap_action(listing, score)
        roadmap.append(
            RoadmapItem(
                listing=listing,
                action=action,
                next_action=next_action_for(listing, action),
                score=round(score, 1),
                estimated_mvp_timeline=listing.build_complexity or "Small (1 week)",
            )
        )
    return sorted(roadmap, key=lambda item: item.score, reverse=True)[:limit]


def next_action_for(listing: Listing, action: str | None = None) -> str:
    if action is None:
        recommendation = (listing.recommendation or "").lower()
        if "build now" in recommendation:
            action = "build now"
        elif "build later" in recommendation or "acquire" in recommendation:
            action = "build later"
        elif "watch" in recommendation:
            action = "watch"
        else:
            action = "research"
    if "build now" in action:
        return "Draft MVP scope and first 10-page SEO/content map."
    if "build later" in action:
        return "Park in roadmap and identify the missing proof point."
    if "watch" in action:
        return "Monitor score movement and seller/traffic changes for one more cycle."
    return "Collect more proof before allocating build time."


def write_opportunity_history_exports(
    memory_records: list[OpportunityMemory],
    export_dir: Path = HISTORY_EXPORT_DIR,
) -> list[Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for memory in memory_records:
        path = export_dir / f"{memory.listing_id}-{_slug(memory.title)}.json"
        path.write_text(json.dumps(memory_to_dict(memory), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def memory_to_dict(memory: OpportunityMemory) -> dict[str, Any]:
    trend = trend_for_memory(memory)
    return {
        "first_seen": memory.first_seen,
        "last_seen": memory.last_seen,
        "title": memory.title,
        "category": memory.category,
        "source": memory.source,
        "current_bend_score": memory.current_bend_score,
        "current_founder_score": memory.current_founder_score,
        "current_recommendation": memory.current_recommendation,
        "historical_bend_scores": memory.historical_bend_scores,
        "historical_founder_scores": memory.historical_founder_scores,
        "recommendation_history": memory.recommendation_history,
        "times_seen": memory.times_seen,
        "notes": memory.notes,
        "trend": trend.label,
        "bend_score_change": trend.bend_score_change,
        "founder_score_change": trend.founder_score_change,
        "recommendation_change": trend.recommendation_change,
    }


def _roadmap_action(listing: Listing, score: float) -> str:
    recommendation = listing.recommendation or ""
    if "BUILD NOW" in recommendation or score >= 86:
        return "build now"
    if "BUILD LATER" in recommendation or score >= 74:
        return "build later"
    return "watch"


def _cluster_keys(listing: Listing) -> set[str]:
    text = f"{listing.title} {listing.category} {listing.description} {listing.seller_notes}".lower()
    words = {word for word in re.findall(r"[a-z0-9]+", listing.title.lower()) if len(word) >= 4}
    keys = {f"category:{listing.category.lower()}", f"source:{listing.source.lower()}"}
    for audience in ["realtor", "real estate", "florida", "outdoor", "shopify", "invoice", "ai", "developer", "travel", "newsletter"]:
        if audience in text:
            keys.add(f"audience:{audience}")
    for word in words:
        keys.add(f"title:{word}")
    return keys


def _cluster_name(key: str, listings: list[Listing]) -> str:
    prefix, value = key.split(":", 1)
    if prefix == "audience":
        return f"{value.title()} Cluster"
    if prefix == "category":
        return f"{value.title()} Cluster"
    if prefix == "title":
        return f"{value.title()} Theme Cluster"
    return f"{listings[0].source} Source Cluster"


def _cluster_reason(key: str, listings: list[Listing]) -> str:
    prefix, value = key.split(":", 1)
    if prefix == "category":
        return f"These opportunities share the {value} category, so lessons, content, and monetization experiments can transfer."
    if prefix == "audience":
        return f"These opportunities point at a shared {value} audience, which can compound into a portfolio wedge."
    if prefix == "title":
        return f"These opportunities reuse the '{value}' concept, suggesting a repeatable content or product angle."
    return "These opportunities came from the same source and should be compared for quality and acquisition terms."


def _average_founder(listings: list[Listing]) -> float:
    return sum(listing.founder_score or 0 for listing in listings) / len(listings)


def _range(values: list[float]) -> float:
    if not values:
        return 0.0
    return max(values) - min(values)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "opportunity"
