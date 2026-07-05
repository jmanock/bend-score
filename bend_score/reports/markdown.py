from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bend_score.ai.ideas import improvement_ideas, why_interesting
from bend_score.analysis.insights import listing_insights, portfolio_observations
from bend_score.core.intelligence import IntelligenceRun
from bend_score.config import REPORT_DIR
from bend_score.memory import (
    FeedbackEntry,
    Movers,
    OpportunityCluster,
    OpportunityMemory,
    RoadmapItem,
    movers_for,
    trend_for_memory,
)
from bend_score.models import Listing, Signal, WatchlistItem
from bend_score.scoring.bend_score import calculate_bend_score


REPORT_PATH = REPORT_DIR / "latest.md"


def write_intelligence_reports(
    intelligence: IntelligenceRun,
    all_signals: list[Signal],
    listings: list[Listing],
    watchlist: list[WatchlistItem],
    memory_records: list[OpportunityMemory] | None = None,
    feedback_entries: list[FeedbackEntry] | None = None,
    clusters: list[OpportunityCluster] | None = None,
    roadmap: list[RoadmapItem] | None = None,
    movers: Movers | None = None,
    report_dir: Path = REPORT_DIR,
) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_path = report_dir / "latest.md"
    dated_path = report_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    content = build_intelligence_report(
        intelligence,
        all_signals,
        listings,
        watchlist,
        memory_records=memory_records,
        feedback_entries=feedback_entries,
        clusters=clusters,
        roadmap=roadmap,
        movers=movers,
    )
    latest_path.write_text(content, encoding="utf-8")
    dated_path.write_text(content, encoding="utf-8")
    return latest_path, dated_path


def build_intelligence_report(
    intelligence: IntelligenceRun,
    all_signals: list[Signal],
    listings: list[Listing],
    watchlist: list[WatchlistItem],
    memory_records: list[OpportunityMemory] | None = None,
    feedback_entries: list[FeedbackEntry] | None = None,
    clusters: list[OpportunityCluster] | None = None,
    roadmap: list[RoadmapItem] | None = None,
    movers: Movers | None = None,
) -> str:
    current_signals = intelligence.signals
    memory_records = memory_records or []
    feedback_entries = feedback_entries or []
    clusters = clusters or []
    roadmap = roadmap or []
    movers = movers or movers_for(memory_records)
    ranked = sorted(
        listings,
        key=lambda listing: ((listing.founder_score or 0), (listing.portfolio_fit or 0), (listing.bend_score or 0)),
        reverse=True,
    )
    lines = [
        "# Bend Score Morning Investment Memo",
        "",
        f"Date generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Executive Summary",
        "",
    ]
    if ranked:
        top = ranked[0]
        lines.append(
            f"- Top decision: **{top.title}** with Founder {(top.founder_score or 0):.0f}/100, "
            f"Portfolio Fit {(top.portfolio_fit or 0):.0f}/100, recommendation **{top.recommendation}**."
        )
    lines.append(f"- Opportunities tracked in memory: {len(memory_records)}")
    lines.append(f"- Signals generated this run: {len(current_signals)}; timeline signals retained: {len(all_signals)}")
    lines.append(f"- Founder feedback notes stored: {len(feedback_entries)}")
    lines.append("")

    lines.extend(_top_three_section(ranked[:3], memory_records))
    lines.extend(_movers_section(movers))
    lines.extend(_clusters_section(clusters))
    lines.extend(_roadmap_section(roadmap))
    lines.extend(_feedback_section(feedback_entries))
    lines.extend(_full_table_section(ranked, memory_records))

    return "\n".join(lines)


def _top_three_section(listings: list[Listing], memory_records: list[OpportunityMemory]) -> list[str]:
    lines = ["## Today's Top 3 Opportunities", ""]
    memory_by_id = {memory.listing_id: memory for memory in memory_records}
    if not listings:
        return lines + ["No listings available.", ""]
    for index, listing in enumerate(listings, start=1):
        trend = trend_for_memory(memory_by_id[listing.id]) if listing.id in memory_by_id else None
        lines.append(f"### {index}. {listing.title}")
        lines.append(f"- Recommendation: {listing.recommendation or 'n/a'}")
        lines.append(f"- Founder Score: {(listing.founder_score or 0):.0f}/100")
        lines.append(f"- Portfolio Fit: {(listing.portfolio_fit or 0):.0f}/100")
        lines.append(f"- Trend: {trend.label if trend else 'NEW'}")
        lines.append(f"- Next action: {listing.executive_summary or 'Review opportunity detail.'}")
        lines.append("")
    return lines


def _movers_section(movers: Movers) -> list[str]:
    lines = ["## Today's Movers", ""]

    def label(memory: OpportunityMemory | None) -> str:
        if memory is None:
            return "n/a"
        trend = trend_for_memory(memory)
        return (
            f"#{memory.listing_id} {memory.title} ({trend.label}, "
            f"Founder {trend.founder_score_change:+.1f}, Bend {trend.bend_score_change:+.1f}, "
            f"seen {trend.times_seen}x)"
        )

    lines.append(f"- Biggest rising opportunity: {label(movers.biggest_rising)}")
    lines.append(f"- Biggest falling opportunity: {label(movers.biggest_falling)}")
    lines.append(
        "- Newly discovered high-potential opportunities: "
        + (", ".join(f"#{memory.listing_id} {memory.title}" for memory in movers.newly_discovered) or "n/a")
    )
    lines.append(f"- Most consistent opportunity: {label(movers.most_consistent)}")
    lines.append(f"- Most volatile opportunity: {label(movers.most_volatile)}")
    lines.append("")
    return lines


def _clusters_section(clusters: list[OpportunityCluster]) -> list[str]:
    lines = ["## Opportunity Clusters", ""]
    if not clusters:
        return lines + ["No strong clusters yet.", ""]
    for cluster in clusters[:5]:
        lines.append(f"### {cluster.name}")
        lines.append(cluster.reason)
        for listing in cluster.listings:
            lines.append(f"- #{listing.id} {listing.title} ({listing.category})")
        lines.append("")
    return lines


def _roadmap_section(roadmap: list[RoadmapItem]) -> list[str]:
    lines = ["## Suggested Build Roadmap", ""]
    if not roadmap:
        return lines + ["No roadmap items available.", ""]
    for index, item in enumerate(roadmap[:5], start=1):
        lines.append(f"{index}. **{item.listing.title}** - {item.action}")
        lines.append(f"   - Roadmap score: {item.score:.1f}")
        lines.append(f"   - Next action: {item.next_action}")
        lines.append(f"   - Estimated MVP timeline: {item.estimated_mvp_timeline}")
    lines.append("")
    return lines


def _feedback_section(feedback_entries: list[FeedbackEntry]) -> list[str]:
    lines = ["## Feedback Notes", ""]
    if not feedback_entries:
        return lines + ["No founder feedback recorded yet.", ""]
    for entry in feedback_entries[:8]:
        note = f" - {entry.note}" if entry.note else ""
        lines.append(f"- #{entry.listing_id} {entry.title}: {entry.reaction}{note}")
    lines.append("")
    return lines


def _full_table_section(listings: list[Listing], memory_records: list[OpportunityMemory]) -> list[str]:
    lines = ["## Full Opportunity Table", ""]
    memory_by_id = {memory.listing_id: memory for memory in memory_records}
    lines.append("| ID | Opportunity | Founder | Bend | Trend | Seen | Recommendation |")
    lines.append("| --- | --- | ---: | ---: | --- | ---: | --- |")
    for listing in listings:
        memory = memory_by_id.get(listing.id)
        trend = trend_for_memory(memory) if memory else None
        lines.append(
            f"| {listing.id} | {listing.title} | {(listing.founder_score or 0):.0f} | "
            f"{(listing.bend_score or 0):.0f} | {trend.label if trend else 'NEW'} | "
            f"{trend.times_seen if trend else 0} | {listing.recommendation or 'n/a'} |"
        )
    lines.append("")
    return lines


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


def _marketplace_listing_section(listings: list[Listing]) -> list[str]:
    lines = ["## Marketplace Opportunity Memos", ""]
    if not listings:
        return lines + ["No listings available.", ""]
    ranked = sorted(
        listings,
        key=lambda listing: ((listing.founder_score or 0), (listing.portfolio_fit or 0), (listing.bend_score or 0)),
        reverse=True,
    )
    for listing in ranked[:10]:
        lines.extend(_memo_block(listing))
    lines.append("")
    return lines


def _github_section(signals: list[Signal]) -> list[str]:
    groups = [
        ("Fast Growth Candidates", {"github_fast_growth_candidate"}),
        ("Abandoned Popular Repos", {"github_abandoned_popular_repo"}),
        ("Commercial Potential", {"github_commercial_potential"}),
        ("AI / Automation Tools", {"github_ai_tool", "github_automation_tool", "github_developer_tool"}),
        ("No Homepage Opportunities", {"github_no_homepage_opportunity"}),
        ("High Issue Demand", {"github_high_issue_demand"}),
    ]
    lines = ["## GitHub Intelligence", ""]
    for title, signal_types in groups:
        matching = [signal for signal in signals if signal.signal_type in signal_types]
        lines.extend([f"### {title}", ""])
        if not matching:
            lines.extend(["No signals.", ""])
            continue
        for signal in sorted(matching, key=lambda item: item.confidence, reverse=True)[:8]:
            metadata = signal.metadata
            lines.append(f"- **{signal.title}**")
            lines.append(f"  - URL: {metadata.get('github_html_url') or metadata.get('html_url') or 'n/a'}")
            lines.append(f"  - Stars: {metadata.get('stars', 0):,}")
            lines.append(f"  - Language: {metadata.get('language') or 'Unknown'}")
            lines.append(f"  - Signal type: {signal.signal_type}")
            lines.append(f"  - Confidence: {signal.confidence}%")
            lines.append(f"  - Recommendation: {signal.recommendation}")
            lines.append(f"  - Why it matters: {signal.description}")
        lines.append("")
    return lines


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
        f"- Founder Score: {(listing.founder_score or 0):.0f}/100",
        f"- Portfolio Fit: {(listing.portfolio_fit or 0):.0f}/100",
        f"- Build Complexity: {listing.build_complexity or 'n/a'}",
        f"- Maintenance: {listing.maintenance_estimate or 'n/a'}",
        f"- Revenue Timeline: {listing.revenue_timeline or 'n/a'} - {listing.revenue_timeline_explanation or 'n/a'}",
        f"- Recommendation: {listing.recommendation} - {listing.recommendation_explanation}",
        f"- Executive Summary: {listing.executive_summary or 'n/a'}",
        f"- Category: {listing.category}",
        f"- Asking price: {_money(listing.asking_price)}",
        f"- Monthly revenue: {_money(listing.monthly_revenue)}",
        f"- Monthly profit: {_money(listing.monthly_profit)}",
        f"- URL: {listing.url}",
        f"- Why it is interesting: {why_interesting(listing)}",
        "- Improvement ideas:",
    ]


def _memo_block(listing: Listing) -> list[str]:
    lines = [
        f"### #{listing.id} {listing.title}",
        "",
        f"- Recommendation: {listing.recommendation or 'n/a'}",
        f"- Bend Score: {(listing.bend_score or 0):.0f}/100",
        f"- Founder Score: {(listing.founder_score or 0):.0f}/100",
        f"- Portfolio Fit: {(listing.portfolio_fit or 0):.0f}/100",
        f"- Build Complexity: {listing.build_complexity or 'n/a'}",
        f"- Maintenance: {listing.maintenance_estimate or 'n/a'}",
        f"- Revenue begins: {listing.revenue_timeline or 'n/a'}",
        f"- Asking price: {_money(listing.asking_price)}",
        f"- Monthly revenue/profit: {_money(listing.monthly_revenue)} / {_money(listing.monthly_profit)}",
        f"- URL: {listing.url}",
        "",
        "Executive Summary:",
        "",
        listing.executive_summary or "No executive summary available.",
        "",
        "Why It Scored Well:",
        "",
    ]
    reasons = [reason.strip() for reason in (listing.founder_reasons or "").splitlines() if reason.strip()]
    if not reasons:
        reasons = ["Founder intelligence has not been calculated yet."]
    lines.extend([f"- {reason}" for reason in reasons])
    lines.extend(
        [
            "",
            "Complexity Notes:",
            "",
            listing.build_complexity_explanation or "No complexity explanation available.",
            "",
            "Timeline Assumption:",
            "",
            listing.revenue_timeline_explanation or "No revenue timeline explanation available.",
            "",
        ]
    )
    return lines


def _compact_section(title: str, listings: list[Listing]) -> list[str]:
    lines = [f"## {title}", ""]
    if not listings:
        lines.extend(["No matching listings.", ""])
        return lines
    for listing in listings:
        lines.append(
            f"- {listing.title}: Bend {(listing.bend_score or 0):.0f}/100, Founder {(listing.founder_score or 0):.0f}/100, "
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
