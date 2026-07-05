from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Iterable

from bend_score.memory import OpportunityMemory, Trend, trend_for_memory
from bend_score.models import Listing, Signal


STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "best",
    "build",
    "business",
    "candidate",
    "code",
    "com",
    "for",
    "founder",
    "free",
    "github",
    "io",
    "new",
    "now",
    "of",
    "opportunity",
    "platform",
    "project",
    "repo",
    "repository",
    "site",
    "software",
    "the",
    "to",
    "tool",
    "tools",
    "with",
}

MARKET_KEYWORDS = {
    "AI": {"ai", "agent", "agents", "automation", "llm", "machine", "prompt", "rag"},
    "Developer Tools": {"api", "cli", "code", "developer", "devtools", "github", "plugin", "sdk", "workflow"},
    "Travel": {"cruise", "deal", "deals", "flight", "florida", "hotel", "local", "rv", "travel"},
    "Finance": {"bank", "cashback", "credit", "cfo", "finance", "invoice", "money", "payment", "stripe"},
    "Local Services": {"local", "pickleball", "realtor", "real", "restaurant", "solar", "wedding"},
    "Marketing": {"analytics", "content", "email", "lead", "marketing", "newsletter", "seo"},
    "SaaS": {"crm", "dashboard", "saas", "subscription", "workflow"},
    "Commerce": {"affiliate", "shopify", "store", "woocommerce"},
}

PORTFOLIO_TARGETS = {"Travel", "Finance", "AI", "Developer Tools", "Local Services", "Marketing", "SaaS"}
STRONG_RECOMMENDATIONS = {"BUILD NOW", "BUILD", "ACQUIRE", "BUY", "BUILD LATER"}
WATCH_RECOMMENDATIONS = {"WATCH", "RESEARCH"}


@dataclass(frozen=True)
class ConsensusEvidence:
    title: str
    source_name: str
    observer_name: str
    category: str
    confidence: int
    recommendation: str
    keywords: set[str]
    market: str
    listing: Listing | None = None
    signal: Signal | None = None
    trend: Trend | None = None


@dataclass(frozen=True)
class ConsensusOpportunity:
    fingerprint: str
    title: str
    market: str
    category: str
    keywords: list[str]
    evidence: list[ConsensusEvidence]
    listings: list[Listing]
    signals: list[Signal]
    observers: list[str]
    consensus_score: float
    heat_score: float
    heat_by_observer: dict[str, float]
    reasons: list[str]

    @property
    def observer_count(self) -> int:
        return len(self.observers)

    @property
    def primary_listing(self) -> Listing | None:
        return self.listings[0] if self.listings else None

    @property
    def primary_recommendation(self) -> str:
        recommendations = [evidence.recommendation for evidence in self.evidence if evidence.recommendation]
        if not recommendations:
            return "RESEARCH"
        return sorted(recommendations, key=_recommendation_rank, reverse=True)[0]


@dataclass(frozen=True)
class PortfolioAllocation:
    market: str
    count: int
    average_consensus: float
    average_heat: float
    status: str
    recommendation: str


def build_consensus(
    listings: Iterable[Listing],
    signals: Iterable[Signal],
    memory_records: Iterable[OpportunityMemory] | None = None,
) -> list[ConsensusOpportunity]:
    memory_by_id = {memory.listing_id: memory for memory in (memory_records or [])}
    evidence = [_evidence_from_listing(listing, memory_by_id.get(listing.id)) for listing in listings]
    evidence.extend(_evidence_from_signal(signal) for signal in signals)
    evidence = [item for item in evidence if item.keywords]

    groups: list[list[ConsensusEvidence]] = []
    for item in sorted(evidence, key=lambda value: (value.market, value.title.lower())):
        match = _best_group(item, groups)
        if match is None:
            groups.append([item])
        else:
            match.append(item)

    opportunities = [_opportunity_from_group(group) for group in groups]
    return sorted(opportunities, key=lambda item: (item.consensus_score, item.heat_score), reverse=True)


def fingerprint_for_opportunity(
    title: str,
    category: str = "",
    tags: Iterable[str] | None = None,
    source: str = "",
    language: str = "",
) -> str:
    keywords = normalized_keywords(" ".join([title, category, source, language, " ".join(tags or [])]))
    market = market_for_keywords(keywords | normalized_keywords(category))
    selected = sorted((keywords - STOPWORDS))[:5]
    return _slug("-".join([market, *selected])) or "general-opportunity"


def top_three_consensus(opportunities: Iterable[ConsensusOpportunity]) -> list[ConsensusOpportunity]:
    return sorted(opportunities, key=_top_three_score, reverse=True)[:3]


def heat_rankings(opportunities: Iterable[ConsensusOpportunity]) -> list[ConsensusOpportunity]:
    return sorted(opportunities, key=lambda item: (item.heat_score, item.consensus_score), reverse=True)


def portfolio_allocation(opportunities: Iterable[ConsensusOpportunity]) -> list[PortfolioAllocation]:
    items = list(opportunities)
    allocation: list[PortfolioAllocation] = []
    for market in sorted(PORTFOLIO_TARGETS | {item.market for item in items}):
        matching = [item for item in items if item.market == market]
        count = len(matching)
        average_consensus = _average(item.consensus_score for item in matching)
        average_heat = _average(item.heat_score for item in matching)
        if count >= 10:
            status = "Overrepresented"
            recommendation = "Prune weaker ideas and only pursue the highest-consensus opportunities."
        elif count <= 1 and market in PORTFOLIO_TARGETS:
            status = "Underrepresented"
            recommendation = "Look for more observers or test a small content wedge."
        elif average_heat >= 7.5:
            status = "Worth expanding"
            recommendation = "Allocate research time because heat and consensus are converging."
        else:
            status = "Balanced"
            recommendation = "Maintain watchlist coverage."
        allocation.append(PortfolioAllocation(market, count, average_consensus, average_heat, status, recommendation))
    return sorted(allocation, key=lambda item: (item.status != "Worth expanding", -item.average_heat, item.market))


def executive_recommendation(opportunities: Iterable[ConsensusOpportunity]) -> dict[str, str]:
    top = top_three_consensus(opportunities)
    build = next((item for item in top if item.consensus_score >= 78 or item.primary_recommendation in STRONG_RECOMMENDATIONS), None)
    watch = next((item for item in top if item is not build), None)
    ignore = min(list(opportunities), key=lambda item: item.consensus_score, default=None)
    return {
        "build": _executive_line(build, "Build") if build else "Build: no consensus-backed build candidate yet.",
        "watch": _executive_line(watch, "Watch") if watch else "Watch: keep collecting observer evidence.",
        "ignore": _executive_line(ignore, "Ignore") if ignore else "Ignore: no low-consensus opportunity identified.",
    }


def consensus_metadata_by_listing(
    listings: Iterable[Listing],
    signals: Iterable[Signal] | None = None,
    memory_records: Iterable[OpportunityMemory] | None = None,
) -> dict[int, dict[str, object]]:
    opportunities = build_consensus(listings, signals or [], memory_records)
    metadata: dict[int, dict[str, object]] = {}
    for opportunity in opportunities:
        for listing in opportunity.listings:
            if listing.id is None:
                continue
            metadata[listing.id] = {
                "consensus_score": round(opportunity.consensus_score, 1),
                "heat_score": round(opportunity.heat_score, 1),
                "observer_count": opportunity.observer_count,
                "observer_names": opportunity.observers,
                "consensus_fingerprint": opportunity.fingerprint,
                "consensus_market": opportunity.market,
                "consensus_keywords": opportunity.keywords,
            }
    return metadata


def normalized_keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    joined: set[str] = set()
    for word in words:
        if word in {"ai", "ml"}:
            joined.add(word)
            continue
        if len(word) < 3 or word in STOPWORDS:
            continue
        if word == "realtors":
            word = "realtor"
        if word == "agents":
            word = "agent"
        joined.add(word)
    return joined


def market_for_keywords(keywords: set[str]) -> str:
    scores = [(market, len(keywords & market_keywords)) for market, market_keywords in MARKET_KEYWORDS.items()]
    market, score = max(scores, key=lambda item: item[1])
    return market if score else "General"


def _evidence_from_listing(listing: Listing, memory: OpportunityMemory | None = None) -> ConsensusEvidence:
    metadata = _json_metadata(listing.seller_notes)
    tags = metadata.get("topics") or []
    language = str(metadata.get("language") or "")
    text = " ".join(
        [
            listing.title,
            listing.category,
            listing.source,
            listing.description,
            listing.tech_stack,
            language,
            " ".join(str(tag) for tag in tags),
        ]
    )
    keywords = normalized_keywords(text)
    return ConsensusEvidence(
        title=listing.title,
        source_name=listing.source or "listing",
        observer_name=_observer_for_listing(listing),
        category=listing.category,
        confidence=round(((listing.bend_score or 0) + (listing.founder_score or 0)) / 2) if listing.founder_score else round(listing.bend_score or 60),
        recommendation=listing.recommendation or "RESEARCH",
        keywords=keywords,
        market=market_for_keywords(keywords | normalized_keywords(listing.category)),
        listing=listing,
        trend=trend_for_memory(memory) if memory else None,
    )


def _evidence_from_signal(signal: Signal) -> ConsensusEvidence:
    metadata = signal.metadata or {}
    tags = metadata.get("topics") or metadata.get("tags") or []
    language = str(metadata.get("language") or "")
    text = " ".join(
        [
            signal.title,
            signal.description,
            signal.category,
            signal.signal_type,
            language,
            " ".join(str(tag) for tag in tags),
        ]
    )
    keywords = normalized_keywords(text)
    return ConsensusEvidence(
        title=signal.title,
        source_name=signal.observer,
        observer_name=signal.observer,
        category=signal.category,
        confidence=signal.confidence,
        recommendation=signal.recommendation,
        keywords=keywords,
        market=market_for_keywords(keywords | normalized_keywords(signal.category)),
        signal=signal,
    )


def _best_group(item: ConsensusEvidence, groups: list[list[ConsensusEvidence]]) -> list[ConsensusEvidence] | None:
    best_group: list[ConsensusEvidence] | None = None
    best_score = 0.0
    for group in groups:
        score = max(_similarity(item, other) for other in group)
        if score > best_score:
            best_score = score
            best_group = group
    return best_group if best_score >= 0.34 else None


def _similarity(left: ConsensusEvidence, right: ConsensusEvidence) -> float:
    if left.market != right.market:
        return 0.0
    union = left.keywords | right.keywords
    if not union:
        return 0.0
    overlap_count = len(left.keywords & right.keywords)
    overlap = overlap_count / len(union)
    keyword_bonus = 0.16 if overlap_count >= 2 else 0.0
    category_bonus = 0.12 if normalized_keywords(left.category) & normalized_keywords(right.category) else 0.0
    observer_bonus = 0.08 if left.observer_name != right.observer_name else 0.0
    return min(1.0, overlap + keyword_bonus + category_bonus + observer_bonus)


def _opportunity_from_group(group: list[ConsensusEvidence]) -> ConsensusOpportunity:
    listings = sorted(
        [item.listing for item in group if item.listing is not None],
        key=lambda listing: ((listing.founder_score or 0), (listing.bend_score or 0)),
        reverse=True,
    )
    signals = [item.signal for item in group if item.signal is not None]
    observers = sorted({item.observer_name for item in group if item.observer_name})
    all_keywords = sorted(set().union(*(item.keywords for item in group)))[:10]
    market = _most_common([item.market for item in group]) or "General"
    category = _most_common([item.category for item in group]) or market
    title = _consensus_title(group, listings, market, all_keywords)
    heat_by_observer = _heat_by_observer(group)
    consensus_score = _consensus_score(group, listings, observers)
    heat_score = _heat_score(group, heat_by_observer)
    return ConsensusOpportunity(
        fingerprint=fingerprint_for_opportunity(title, category, all_keywords, market),
        title=title,
        market=market,
        category=category,
        keywords=all_keywords,
        evidence=group,
        listings=listings,
        signals=signals,
        observers=observers,
        consensus_score=round(consensus_score, 1),
        heat_score=round(heat_score, 1),
        heat_by_observer=heat_by_observer,
        reasons=_reasons_for(group, consensus_score, heat_score, observers),
    )


def _consensus_score(group: list[ConsensusEvidence], listings: list[Listing], observers: list[str]) -> float:
    observer_score = min(100, 42 + (len(observers) * 14))
    founder = _average((listing.founder_score or 0) for listing in listings) or _average(item.confidence for item in group)
    bend = _average((listing.bend_score or 0) for listing in listings) or _average(item.confidence for item in group)
    portfolio = _average((listing.portfolio_fit or 0) for listing in listings) or 55
    confidence = _average(item.confidence for item in group)
    trend = _trend_score([item.trend for item in group if item.trend])
    agreement = _recommendation_agreement(group)
    return max(
        0,
        min(
            100,
            observer_score * 0.24
            + founder * 0.20
            + bend * 0.16
            + portfolio * 0.13
            + trend * 0.10
            + agreement * 0.09
            + confidence * 0.08,
        ),
    )


def _heat_score(group: list[ConsensusEvidence], heat_by_observer: dict[str, float]) -> float:
    observer_heat = min(10.0, 3.2 + len(heat_by_observer) * 1.45)
    confidence_heat = _average(item.confidence for item in group) / 10
    keyword_density = min(10.0, 3.0 + math.log(len(set().union(*(item.keywords for item in group))) + 1, 2))
    impact_heat = _average(heat_by_observer.values())
    return max(0.0, min(10.0, observer_heat * 0.36 + confidence_heat * 0.28 + keyword_density * 0.16 + impact_heat * 0.20))


def _heat_by_observer(group: list[ConsensusEvidence]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for item in group:
        values.setdefault(item.observer_name, []).append(min(10.0, max(1.0, item.confidence / 10)))
    return {observer: round(_average(scores), 1) for observer, scores in sorted(values.items())}


def _recommendation_agreement(group: list[ConsensusEvidence]) -> float:
    recommendations = [item.recommendation for item in group if item.recommendation]
    if not recommendations:
        return 55.0
    counts: dict[str, int] = {}
    for recommendation in recommendations:
        family = _recommendation_family(recommendation)
        counts[family] = counts.get(family, 0) + 1
    return 55 + (max(counts.values()) / len(recommendations)) * 45


def _trend_score(trends: list[Trend]) -> float:
    if not trends:
        return 58.0
    labels = [trend.label for trend in trends]
    if "RISING" in labels:
        return 88.0
    if "NEW" in labels:
        return 72.0
    if "STABLE" in labels:
        return 65.0
    if "FALLING" in labels:
        return 35.0
    return 55.0


def _top_three_score(item: ConsensusOpportunity) -> float:
    complexity_bonus = 8 if (item.primary_listing and item.primary_listing.build_complexity in {"Tiny (1-2 days)", "Small (1 week)"}) else 0
    return item.consensus_score * 0.48 + item.heat_score * 4.2 + item.observer_count * 4 + complexity_bonus


def _reasons_for(group: list[ConsensusEvidence], consensus_score: float, heat_score: float, observers: list[str]) -> list[str]:
    reasons = [
        f"{len(observers)} observer source{'s' if len(observers) != 1 else ''} point at the same market.",
        f"Consensus score is {consensus_score:.1f}/100 and heat is {heat_score:.1f}/10.",
    ]
    if _average(item.confidence for item in group) >= 80:
        reasons.append("Average signal confidence is high.")
    if any(item.recommendation in STRONG_RECOMMENDATIONS for item in group):
        reasons.append("At least one source recommends a build or acquisition action.")
    if len(set().union(*(item.keywords for item in group))) >= 6:
        reasons.append("The fingerprint has enough keyword overlap to avoid being a thin match.")
    return reasons


def _consensus_title(group: list[ConsensusEvidence], listings: list[Listing], market: str, keywords: list[str]) -> str:
    if listings:
        title = re.sub(r"^GitHub Opportunity:\s*", "", listings[0].title).strip()
        if title:
            return title
    important = [keyword.title() for keyword in keywords[:3]]
    return f"{' '.join(important) or market} Opportunity"


def _observer_for_listing(listing: Listing) -> str:
    if listing.source.lower() == "github":
        return "github"
    return listing.source.lower().replace(" ", "_") or "listing"


def _json_metadata(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _most_common(values: Iterable[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0] if counts else ""


def _average(values: Iterable[float]) -> float:
    numbers = [float(value) for value in values if value is not None]
    return sum(numbers) / len(numbers) if numbers else 0.0


def _recommendation_family(recommendation: str) -> str:
    upper = recommendation.upper()
    if any(term in upper for term in STRONG_RECOMMENDATIONS):
        return "build"
    if any(term in upper for term in WATCH_RECOMMENDATIONS):
        return "watch"
    return "ignore"


def _recommendation_rank(recommendation: str) -> int:
    upper = recommendation.upper()
    if "BUILD NOW" in upper:
        return 6
    if "ACQUIRE" in upper or "BUY" in upper:
        return 5
    if "BUILD" in upper:
        return 4
    if "WATCH" in upper:
        return 3
    if "RESEARCH" in upper:
        return 2
    return 1


def _executive_line(opportunity: ConsensusOpportunity | None, label: str) -> str:
    if opportunity is None:
        return f"{label}: no candidate."
    return (
        f"{label}: {opportunity.title} because consensus is {opportunity.consensus_score:.1f}/100, "
        f"heat is {opportunity.heat_score:.1f}/10, and observers include {', '.join(opportunity.observers)}."
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
