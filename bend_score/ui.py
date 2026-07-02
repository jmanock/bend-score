from __future__ import annotations

from bend_score.models import Listing, WatchlistItem


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
            f"Traffic {listing.traffic_estimate:,}"
        )


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


def _listing_line(index: int, listing: Listing) -> str:
    return (
        f"{index:>2}. {_score_color(listing.bend_score or 0)}{listing.bend_score:>5.1f}/100{RESET}  "
        f"{_recommendation_color(listing.recommendation or '')}{listing.recommendation:<8}{RESET}  "
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
    if recommendation == "BUY":
        return GREEN
    if recommendation == "RESEARCH":
        return CYAN
    if recommendation == "WATCH":
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

