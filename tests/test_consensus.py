from __future__ import annotations

import unittest

from bend_score.exporters.morning_content import signal_for_listing
from bend_score.intelligence.consensus import (
    build_consensus,
    consensus_metadata_by_listing,
    fingerprint_for_opportunity,
    heat_rankings,
    portfolio_allocation,
    top_three_consensus,
)
from bend_score.models import Listing, Signal, utc_now


class ConsensusIntelligenceTest(unittest.TestCase):
    def test_fingerprint_generation_is_stable(self) -> None:
        first = fingerprint_for_opportunity("AI Realtor CRM", "SaaS", ["ai", "realtor"], "GitHub", "Python")
        second = fingerprint_for_opportunity("AI Realtor CRM", "SaaS", ["realtor", "ai"], "GitHub", "Python")

        self.assertEqual(first, second)
        self.assertIn("ai", first)

    def test_consensus_merges_related_observer_signals(self) -> None:
        listing = _listing("AI Realtor CRM", source="GitHub", category="GitHub Opportunity")
        signals = [
            _signal("google_trends", "AI Realtor search interest", "AI Realtor demand is climbing."),
            _signal("reddit", "Need software for real estate paperwork", "Realtors need AI paperwork automation."),
        ]

        opportunities = build_consensus([listing], signals)
        match = opportunities[0]

        self.assertGreaterEqual(match.observer_count, 3)
        self.assertGreater(match.consensus_score, 70)
        self.assertEqual(match.market, "AI")

    def test_heat_calculation_ranks_multi_observer_opportunity(self) -> None:
        hot = _listing("AI Realtor CRM", source="GitHub")
        cold = _listing("Kayak Route Blog", source="Manual", category="Content Site", founder_score=50, bend_score=45)
        signals = [
            _signal("google_trends", "AI Realtor trend", "AI Realtor trend"),
            _signal("reddit", "AI Realtor paperwork", "AI Realtor paperwork"),
        ]

        rankings = heat_rankings(build_consensus([hot, cold], signals))

        self.assertIn("AI", rankings[0].market)
        self.assertGreaterEqual(rankings[0].heat_score, rankings[-1].heat_score)

    def test_portfolio_allocation_marks_underrepresented_markets(self) -> None:
        opportunities = build_consensus([_listing("AI Realtor CRM", source="GitHub")], [])

        allocation = portfolio_allocation(opportunities)
        finance = next(item for item in allocation if item.market == "Finance")

        self.assertEqual(finance.status, "Underrepresented")

    def test_top_three_generation_prefers_consensus(self) -> None:
        listings = [
            _listing("AI Realtor CRM", source="GitHub"),
            _listing("Developer Workflow API", source="GitHub", category="GitHub Opportunity"),
            _listing("Florida Travel Deals", source="Acquire", category="Affiliate Site"),
            _listing("Weak Blog", source="Manual", category="Content Site", founder_score=40, bend_score=35),
        ]
        signals = [_signal("reddit", "AI Realtor paperwork", "AI realtor paperwork problem")]

        top = top_three_consensus(build_consensus(listings, signals))

        self.assertEqual(len(top), 3)
        self.assertGreaterEqual(top[0].observer_count, 2)

    def test_consensus_export_metadata(self) -> None:
        listing = _listing("AI Realtor CRM", source="GitHub")
        metadata = consensus_metadata_by_listing([listing], [_signal("reddit", "AI Realtor paperwork", "AI realtor paperwork")])

        signal = signal_for_listing(listing, consensus_metadata=metadata[listing.id])
        exported = signal["metadata"]

        self.assertIn("consensus_score", exported)
        self.assertIn("heat_score", exported)
        self.assertIn("observer_count", exported)
        self.assertIn("observer_names", exported)


def _listing(
    title: str,
    source: str = "GitHub",
    category: str = "SaaS",
    founder_score: float = 88,
    bend_score: float = 82,
) -> Listing:
    now = utc_now()
    return Listing(
        id=abs(hash((title, source))) % 100000,
        title=title,
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        source=source,
        category=category,
        asking_price=10000,
        monthly_revenue=1000,
        monthly_profit=700,
        traffic_estimate=12000,
        description=f"{title} with automation, AI, API, SEO, and SaaS wrapper potential.",
        seller_notes='{"topics": ["ai", "automation", "realtor"], "language": "Python"}',
        tech_stack="Python, API, React",
        created_at=now,
        updated_at=now,
        bend_score=bend_score,
        founder_score=founder_score,
        portfolio_fit=82,
        build_complexity="Small (1 week)",
        revenue_timeline="3 months",
        recommendation="BUILD NOW",
    )


def _signal(observer: str, title: str, description: str) -> Signal:
    return Signal.create(
        observer=observer,
        signal_type="market_signal",
        title=title,
        description=description,
        category="SaaS",
        confidence=88,
        impact="high",
        recommendation="BUILD",
        metadata={"tags": ["ai", "realtor", "automation"]},
    )


if __name__ == "__main__":
    unittest.main()
