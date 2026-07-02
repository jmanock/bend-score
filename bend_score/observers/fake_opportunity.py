from __future__ import annotations

from typing import Any

from bend_score.collectors.sample_data import sample_listings
from bend_score.models import Signal
from bend_score.observers.base import Observer
from bend_score.utils.confidence import weighted_confidence


class FakeOpportunityObserver(Observer):
    name = "fake_opportunity"
    label = "Fake Opportunity Observer"

    def collect(self) -> list[dict[str, Any]]:
        return [listing.__dict__ for listing in sample_listings()]

    def normalize(self, raw_items: list[dict[str, Any]]) -> list[Signal]:
        signals: list[Signal] = []
        for item in raw_items:
            signals.append(_opportunity_signal(item))
            if item["traffic_estimate"] >= 8000 and item["monthly_revenue"] < 500:
                signals.append(_monetization_gap_signal(item))
            if item["monthly_revenue"] >= 750:
                signals.append(_revenue_proof_signal(item))
            if item["category"] in {"Content Site", "Affiliate Site", "Domain", "Newsletter"}:
                signals.append(_seo_signal(item))
        return signals


def _opportunity_signal(item: dict[str, Any]) -> Signal:
    confidence = weighted_confidence(
        [
            (80 if item["traffic_estimate"] > 0 else 45, 1),
            (86 if item["monthly_revenue"] > 0 else 55, 1),
            (75 if item["asking_price"] <= 20000 else 58, 1),
        ]
    )
    return Signal.create(
        observer=FakeOpportunityObserver.name,
        signal_type="opportunity_detected",
        title=item["title"],
        description=item["description"],
        category=item["category"],
        confidence=confidence,
        impact="high" if confidence >= 80 else "medium",
        recommendation=_recommendation(confidence, item),
        metadata=_metadata(item),
    )


def _monetization_gap_signal(item: dict[str, Any]) -> Signal:
    return Signal.create(
        observer=FakeOpportunityObserver.name,
        signal_type="monetization_gap",
        title=f"Monetization gap: {item['title']}",
        description="Meaningful traffic appears under-monetized.",
        category=item["category"],
        confidence=88,
        impact="high",
        recommendation="BUILD",
        metadata=_metadata(item),
    )


def _revenue_proof_signal(item: dict[str, Any]) -> Signal:
    confidence = weighted_confidence(
        [
            (92, 2),
            (85 if item["monthly_profit"] > 0 else 55, 1),
            (80 if item["asking_price"] <= 30000 else 65, 1),
        ]
    )
    return Signal.create(
        observer=FakeOpportunityObserver.name,
        signal_type="revenue_proof",
        title=f"Revenue proof: {item['title']}",
        description="Listing has existing monthly revenue.",
        category=item["category"],
        confidence=confidence,
        impact="high" if item["monthly_profit"] >= 750 else "medium",
        recommendation="RESEARCH",
        metadata=_metadata(item),
    )


def _seo_signal(item: dict[str, Any]) -> Signal:
    confidence = weighted_confidence(
        [
            (90 if item["traffic_estimate"] >= 10000 else 70, 2),
            (82 if item["category"] in {"Content Site", "Affiliate Site"} else 65, 1),
        ]
    )
    return Signal.create(
        observer=FakeOpportunityObserver.name,
        signal_type="seo_upside",
        title=f"SEO upside: {item['title']}",
        description="Organic-friendly asset with room for content or landing-page expansion.",
        category=item["category"],
        confidence=confidence,
        impact="high" if confidence >= 82 else "medium",
        recommendation="WATCH",
        metadata=_metadata(item),
    )


def _recommendation(confidence: int, item: dict[str, Any]) -> str:
    if item["monthly_profit"] >= 700 and item["asking_price"] <= 20000:
        return "BUY"
    if item["monthly_revenue"] == 0 and item["category"] in {"Domain", "Newsletter"}:
        return "BUILD"
    if confidence >= 70:
        return "WATCH"
    return "RESEARCH"


def _metadata(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": item["url"],
        "source": item["source"],
        "asking_price": item["asking_price"],
        "monthly_revenue": item["monthly_revenue"],
        "monthly_profit": item["monthly_profit"],
        "traffic_estimate": item["traffic_estimate"],
        "seller_notes": item["seller_notes"],
        "tech_stack": item["tech_stack"],
    }
