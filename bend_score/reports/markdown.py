from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bend_score.ai.ideas import improvement_ideas, why_interesting
from bend_score.analysis.insights import listing_insights, portfolio_observations
from bend_score.core.intelligence import IntelligenceRun
from bend_score.config import REPORT_DIR
from bend_score.models import Listing, Signal, WatchlistItem
from bend_score.scoring.bend_score import calculate_bend_score


REPORT_PATH = REPORT_DIR / "latest.md"


def write_intelligence_reports(
    intelligence: IntelligenceRun,
    all_signals: list[Signal],
    listings: list[Listing],
    watchlist: list[WatchlistItem],
    report_dir: Path = REPORT_DIR,
) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_path = report_dir / "latest.md"
    dated_path = report_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    content = build_intelligence_report(intelligence, all_signals, listings, watchlist)
    latest_path.write_text(content, encoding="utf-8")
    dated_path.write_text(content, encoding="utf-8")
    return latest_path, dated_path


def build_intelligence_report(
    intelligence: IntelligenceRun,
    all_signals: list[Signal],
    listings: list[Listing],
    watchlist: list[WatchlistItem],
) -> str:
    current_signals = intelligence.signals
    high_confidence = sorted(
        [signal for signal in current_signals if signal.confidence >= 80],
        key=lambda signal: signal.confidence,
        reverse=True,
    )
    lines = [
        "# Today's Intelligence",
        "",
        f"Date generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Signals generated today: {len(current_signals)}",
        f"Signals in timeline: {len(all_signals)}",
        "",
        "## High Confidence Signals",
        "",
    ]
    lines.extend(_signal_lines(high_confidence[:12]))

    for recommendation in ["BUY", "WATCH", "BUILD", "RESEARCH", "IGNORE"]:
        matching = [signal for signal in current_signals if signal.recommendation == recommendation]
        lines.extend([f"## {recommendation}", ""])
        lines.extend(_signal_lines(matching[:10]))

    lines.extend(["## Signal Summary", ""])
    lines.append(f"- Generated this run: {len(current_signals)}")
    lines.append(f"- Average confidence: {intelligence.average_confidence:.1f}%")
    lines.append(f"- Highest confidence: {intelligence.highest_confidence}%")
    lines.append(f"- Timeline snapshots stored: {len(all_signals)}")
    lines.append("")

    lines.extend(["## Statistics", ""])
    lines.append(f"- Listings in database: {len(listings)}")
    lines.append(f"- Watchlist items: {len(watchlist)}")
    if listings:
        average_score = sum(listing.bend_score or 0 for listing in listings) / len(listings)
        lines.append(f"- Average Bend Score: {average_score:.1f}")
    lines.append("")

    lines.extend(["## Observer Summary", ""])
    if not intelligence.observer_results:
        lines.append("- No observers enabled.")
    for result in intelligence.observer_results:
        average = (
            sum(signal.confidence for signal in result.signals) / len(result.signals)
            if result.signals
            else 0
        )
        highest = max([signal.confidence for signal in result.signals], default=0)
        lines.append(f"- {result.label}:")
        lines.append(f"  - Signals generated: {len(result.signals)}")
        lines.append(f"  - Raw facts collected: {result.raw_count}")
        lines.append(f"  - Average confidence: {average:.1f}%")
        lines.append(f"  - Highest confidence: {highest}%")
        lines.append(f"  - Runtime: {result.runtime_seconds:.3f}s")
    lines.append("")

    lines.extend(["## Recommendations", ""])
    recommendations = _recommendation_summary(current_signals)
    lines.extend([f"- {line}" for line in recommendations])
    lines.append("")

    return "\n".join(lines)


def _signal_lines(signals: list[Signal]) -> list[str]:
    if not signals:
        return ["No signals.", ""]
    lines: list[str] = []
    for signal in signals:
        lines.append(
            f"- **{signal.title}** ({signal.signal_type}, {signal.category}) - "
            f"{signal.confidence}% confidence, {signal.impact} impact"
        )
        lines.append(f"  - Recommendation: {signal.recommendation}")
        lines.append(f"  - {signal.description}")
    lines.append("")
    return lines


def _recommendation_summary(signals: list[Signal]) -> list[str]:
    if not signals:
        return ["Enable at least one observer to generate recommendations."]
    counts: dict[str, int] = {}
    for signal in signals:
        counts[signal.recommendation] = counts.get(signal.recommendation, 0) + 1
    return [
        f"{recommendation}: {counts.get(recommendation, 0)} signals"
        for recommendation in ["BUY", "BUILD", "WATCH", "RESEARCH", "IGNORE"]
    ]


def write_reports(
    listings: list[Listing],
    watchlist: list[WatchlistItem],
    report_dir: Path = REPORT_DIR,
) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_path = report_dir / "latest.md"
    dated_path = report_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    content = build_report(listings, watchlist)
    latest_path.write_text(content, encoding="utf-8")
    dated_path.write_text(content, encoding="utf-8")
    return latest_path, dated_path


def write_latest_report(listings: list[Listing], report_path: Path = REPORT_PATH) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    content = build_report(listings, [])
    report_path.write_text(content, encoding="utf-8")
    return report_path


def build_report(listings: list[Listing], watchlist: list[WatchlistItem]) -> str:
    ranked = sorted(listings, key=lambda item: item.bend_score or 0, reverse=True)
    highest_revenue = sorted(listings, key=lambda item: item.monthly_revenue, reverse=True)
    highest_roi = sorted(listings, key=_roi_sort, reverse=True)
    automation = sorted(listings, key=lambda item: _component_score(item, "automation"), reverse=True)
    seo = sorted(listings, key=lambda item: _component_score(item, "seo"), reverse=True)
    today = datetime.now().date().isoformat()
    added_today = [listing for listing in listings if listing.created_at.startswith(today)]
    lines = [
        "# Bend Score Acquisition Intelligence Report",
        "",
        f"Date generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total listings analyzed: {len(listings)}",
        "",
        "## Top Opportunities",
        "",
    ]

    for index, listing in enumerate(ranked[:10], start=1):
        lines.extend(_listing_block(index, listing))
        lines.extend([f"  - {idea}" for idea in improvement_ideas(listing)])
        lines.extend(["- Insights:"])
        lines.extend([f"  - {insight}" for insight in listing_insights(listing)])
        lines.append("")

    lines.extend(_compact_section("Highest Revenue", highest_revenue[:5]))
    lines.extend(_compact_section("Highest ROI Potential", highest_roi[:5]))
    lines.extend(_compact_section("Most Automation Potential", automation[:5]))
    lines.extend(_compact_section("Best SEO Opportunities", seo[:5]))
    lines.extend(_compact_section("Businesses Added Today", added_today[:10]))
    lines.extend(_watchlist_section(watchlist))

    lines.extend(["## Interesting Observations", ""])
    lines.extend([f"- {observation}" for observation in portfolio_observations(listings)])
    lines.append("")

    return "\n".join(lines)


def _listing_block(index: int, listing: Listing) -> list[str]:
    return [
        f"### {index}. {listing.title}",
        "",
        f"- Bend Score: {listing.bend_score:.0f}/100",
        f"- Recommendation: {listing.recommendation} - {listing.recommendation_explanation}",
        f"- Category: {listing.category}",
        f"- Asking price: {_money(listing.asking_price)}",
        f"- Monthly revenue: {_money(listing.monthly_revenue)}",
        f"- Monthly profit: {_money(listing.monthly_profit)}",
        f"- URL: {listing.url}",
        f"- Why it is interesting: {why_interesting(listing)}",
        "- Improvement ideas:",
    ]


def _compact_section(title: str, listings: list[Listing]) -> list[str]:
    lines = [f"## {title}", ""]
    if not listings:
        lines.extend(["No matching listings.", ""])
        return lines
    for listing in listings:
        lines.append(
            f"- {listing.title}: {listing.bend_score:.0f}/100, "
            f"{listing.category}, {_money(listing.asking_price)} asking, "
            f"{_money(listing.monthly_revenue)}/mo revenue"
        )
    lines.append("")
    return lines


def _watchlist_section(watchlist: list[WatchlistItem]) -> list[str]:
    lines = ["## Watchlist Summary", ""]
    if not watchlist:
        lines.extend(["No businesses are currently on the watchlist.", ""])
        return lines
    for item in watchlist:
        title = item.listing.title if item.listing else f"Listing #{item.listing_id}"
        score = item.listing.bend_score if item.listing else 0
        lines.append(f"- {title}: {item.status}, {score:.0f}/100")
    lines.append("")
    return lines


def _component_score(listing: Listing, component: str) -> int:
    result = calculate_bend_score(listing)
    return result.components[component]["score"]


def _roi_sort(listing: Listing) -> float:
    if listing.asking_price <= 0:
        return 0
    return (listing.monthly_profit * 12) / listing.asking_price


def _money(value: float) -> str:
    return f"${value:,.0f}"
