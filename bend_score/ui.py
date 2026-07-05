from __future__ import annotations

from bend_score.ai.ideas import improvement_ideas
from bend_score.models import Listing, Signal, WatchlistItem
from bend_score.scoring.bend_score import calculate_bend_score
from bend_score.scoring.founder_score import calculate_founder_score


RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
DIM = "\033[2m"


def header(title: str = "Today's Intelligence Report") -> None:
    print()
    print(f"{BOLD}{CYAN}================================={RESET}")
    print(f"{BOLD}{CYAN}BEND SCORE{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{CYAN}================================={RESET}")


def section(title: str) -> None:
    print()
    print(f"{BOLD}{title}{RESET}")
    print("-" * len(title))


def print_listings(listings: list[Listing], limit: int | None = None) -> None:
    shown = listings[:limit] if limit else listings
    if not shown:
        print("No listings found.")
        return
    for index, listing in enumerate(shown, start=1):
        print(_listing_line(index, listing))
        print(
            f"    Asking {_money(listing.asking_price)} | "
            f"Revenue {_money(listing.monthly_revenue)}/mo | "
            f"Profit {_money(listing.monthly_profit)}/mo | "
            f"Traffic {listing.traffic_estimate:,} | "
            f"Founder {(listing.founder_score or 0):.1f} | "
            f"Fit {(listing.portfolio_fit or 0):.1f}"
        )


def print_recent_listings(listings: list[Listing]) -> None:
    if not listings:
        print("No listings found.")
        return
    for listing in listings:
        print(
            f"#{listing.id:<4} {listing.title} | {listing.source} | {listing.category} | "
            f"Ask {_money(listing.asking_price)} | Rev {_money(listing.monthly_revenue)}/mo | "
            f"Profit {_money(listing.monthly_profit)}/mo | Bend {(listing.bend_score or 0):.1f} | "
            f"Founder {(listing.founder_score or 0):.1f}"
        )


def print_listing_detail(listing: Listing, watchlist_status: str | None = None) -> None:
    result = calculate_bend_score(listing)
    print(f"ID: {listing.id}")
    print(f"Title: {listing.title}")
    print(f"URL: {listing.url or 'n/a'}")
    print(f"Source: {listing.source}")
    print(f"Category: {listing.category}")
    print(f"Asking price: {_money(listing.asking_price)}")
    print(f"Monthly revenue: {_money(listing.monthly_revenue)}")
    print(f"Monthly profit: {_money(listing.monthly_profit)}")
    print(f"Traffic estimate: {listing.traffic_estimate:,}")
    print(f"Description: {listing.description or 'n/a'}")
    print(f"Seller notes: {listing.seller_notes or 'n/a'}")
    print(f"Tech stack: {listing.tech_stack or 'n/a'}")
    print(f"Created: {listing.created_at}")
    print(f"Updated: {listing.updated_at}")
    print(f"Bend Score: {(listing.bend_score or result.total):.1f}/100")
    print(f"Founder Score: {(listing.founder_score or 0):.1f}/100")
    print(f"Portfolio Fit: {(listing.portfolio_fit or 0):.1f}/100")
    print(f"Build complexity: {listing.build_complexity or 'n/a'}")
    print(f"Maintenance: {listing.maintenance_estimate or 'n/a'}")
    print(f"Revenue timeline: {listing.revenue_timeline or 'n/a'}")
    print(f"Recommendation: {listing.recommendation or result.recommendation}")
    print(f"Recommendation reason: {listing.recommendation_explanation or result.recommendation_explanation}")
    print(f"Executive summary: {listing.executive_summary or 'n/a'}")
    print(f"Watchlist status: {watchlist_status or 'Not watched'}")
    print()
    print("Score breakdown:")
    for name, component in result.components.items():
        label = name.replace("_", " ").title()
        print(f"  {label}: {component['score']}/10 ({component['confidence']}% confidence)")
        print(f"    {component['explanation']}")
    print()
    print("Founder score reasons:")
    founder = calculate_founder_score(listing)
    for reason in founder.reasons:
        print(f"  - {reason}")
    print()
    print("Improvement ideas:")
    for idea in improvement_ideas(listing):
        print(f"  - {idea}")


def print_watchlist(items: list[WatchlistItem]) -> None:
    if not items:
        print("No watchlist items yet.")
        return
    for item in items:
        listing = item.listing
        title = listing.title if listing else f"Listing #{item.listing_id}"
        score = listing.bend_score if listing else 0
        print(f"{item.listing_id:>3}. {_status_color(item.status)}{item.status:<11}{RESET} {score:>5.1f}/100  {title}")
        if item.notes:
            latest = item.notes.splitlines()[-1]
            print(f"     {DIM}{latest}{RESET}")


def print_stats(stats: dict[str, object]) -> None:
    print(f"Total businesses: {stats['total']}")
    print(f"Average Bend Score: {stats['average_bend_score']:.1f}")
    print(f"Average Founder Score: {stats['average_founder_score']:.1f}")
    print(f"Average Portfolio Fit: {stats['average_portfolio_fit']:.1f}")
    print(f"Highest score: {stats['highest_score']:.1f}")
    print(f"Lowest score: {stats['lowest_score']:.1f}")
    print(f"Average asking price: {_money(stats['average_asking_price'])}")
    print(f"Average revenue: {_money(stats['average_revenue'])}/mo")
    print(f"Average profit: {_money(stats['average_profit'])}/mo")
    print(f"Average revenue multiple: {stats['average_revenue_multiple']:.1f}x monthly profit")
    print()
    print("Businesses by category:")
    for category, count in sorted(stats["by_category"].items()):
        print(f"  {category}: {count}")


def print_signals(signals: list[Signal]) -> None:
    if not signals:
        print("No signals found.")
        return
    for signal in signals:
        print(
            f"{_score_color(signal.confidence)}{signal.confidence:>3}%{RESET}  "
            f"{_recommendation_color(signal.recommendation)}{signal.recommendation:<8}{RESET}  "
            f"{signal.observer:<16} {signal.title}"
        )
        print(f"     {signal.signal_type} | {signal.impact} impact | {signal.timestamp}")
        if signal.metadata.get("github_html_url"):
            print(f"     {signal.metadata['github_html_url']}")


def _listing_line(index: int, listing: Listing) -> str:
    return (
        f"{index:>2}. {_score_color(listing.bend_score or 0)}{(listing.bend_score or 0):>5.1f}/100{RESET}  "
        f"F:{(listing.founder_score or 0):>5.1f}  "
        f"{_recommendation_color(listing.recommendation or '')}{(listing.recommendation or 'n/a'):<18}{RESET}  "
        f"#{listing.id} {listing.title} {DIM}({listing.category}){RESET}"
    )


def _money(value: object) -> str:
    return f"${float(value):,.0f}"


def _score_color(score: float) -> str:
    if score >= 75:
        return GREEN
    if score >= 55:
        return YELLOW
    return RED


def _recommendation_color(recommendation: str) -> str:
    if "BUILD NOW" in recommendation:
        return GREEN
    if "ACQUIRE" in recommendation:
        return GREEN
    if "BUILD LATER" in recommendation or "RESEARCH" in recommendation:
        return CYAN
    if "WATCH" in recommendation:
        return YELLOW
    return RED


def _status_color(status: str) -> str:
    if status in {"Interested", "Purchased"}:
        return GREEN
    if status in {"Researching", "Contacted"}:
        return CYAN
    if status == "Passed":
        return RED
    return YELLOW
