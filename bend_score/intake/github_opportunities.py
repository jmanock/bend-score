from __future__ import annotations

import json
from typing import Iterable

from bend_score.models import Listing, Signal, utc_now


CONVERTIBLE_SIGNAL_TYPES = {
    "github_fast_growth_candidate",
    "github_abandoned_popular_repo",
    "github_commercial_potential",
    "github_ai_tool",
    "github_automation_tool",
    "github_developer_tool",
    "github_no_homepage_opportunity",
    "github_high_issue_demand",
    "github_founder_profile_match",
}


def github_signal_to_listing(signal: Signal) -> Listing | None:
    if signal.observer != "github" or signal.signal_type not in CONVERTIBLE_SIGNAL_TYPES:
        return None
    metadata = signal.metadata
    url = metadata.get("github_html_url") or metadata.get("html_url")
    full_name = metadata.get("github_full_name") or metadata.get("full_name") or signal.title
    if not url:
        return None

    stars = int(metadata.get("stars") or 0)
    forks = int(metadata.get("forks") or 0)
    issues = int(metadata.get("open_issues") or 0)
    language = metadata.get("language") or "Unknown"
    topics = metadata.get("topics") or []
    topic_text = ", ".join(str(topic) for topic in topics)
    description = metadata.get("description") or signal.description
    now = utc_now()

    return Listing(
        id=None,
        title=f"GitHub Opportunity: {full_name}",
        url=str(url),
        source="GitHub",
        category="GitHub Opportunity",
        asking_price=0,
        monthly_revenue=0,
        monthly_profit=0,
        traffic_estimate=max(stars, 0),
        description=(
            f"{description} GitHub signal: {signal.description} "
            f"Stars: {stars:,}. Forks: {forks:,}. Open issues: {issues:,}."
        ),
        seller_notes=json.dumps(metadata, sort_keys=True),
        tech_stack=f"{language}; topics: {topic_text}; license: {metadata.get('license') or 'unknown'}",
        created_at=now,
        updated_at=now,
    )


def github_signals_to_listings(signals: Iterable[Signal]) -> list[Listing]:
    listings: list[Listing] = []
    seen_urls: set[str] = set()
    for signal in signals:
        listing = github_signal_to_listing(signal)
        if listing is None or listing.url in seen_urls:
            continue
        seen_urls.add(listing.url)
        listings.append(listing)
    return listings


def github_metadata_from_listing(listing: Listing) -> dict[str, object]:
    if listing.source != "GitHub":
        return {}
    try:
        metadata = json.loads(listing.seller_notes or "{}")
    except json.JSONDecodeError:
        return {}
    return metadata if isinstance(metadata, dict) else {}
