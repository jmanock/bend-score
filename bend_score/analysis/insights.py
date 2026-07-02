from __future__ import annotations

from bend_score.models import Listing
from bend_score.scoring.common import revenue_multiple


def listing_insights(listing: Listing) -> list[str]:
    insights: list[str] = []
    multiple = revenue_multiple(listing)
    category = listing.category.lower()

    if category == "saas" and multiple is not None and multiple <= 18:
        insights.append("This SaaS is priced below similar small software businesses.")
    if category in {"content site", "affiliate site"} and listing.traffic_estimate >= 10000 and listing.monthly_revenue < 500:
        insights.append("This content asset has high traffic but weak monetization.")
    if category in {"content site", "affiliate site", "newsletter", "domain"} and listing.traffic_estimate >= 8000:
        insights.append("This business has excellent SEO upside.")
    if multiple is not None and multiple > 36:
        insights.append("This business appears overpriced relative to monthly profit.")
    if multiple is not None and multiple <= 18:
        insights.append("Revenue multiple is attractive.")
    if listing.monthly_revenue == 0 and listing.asking_price > 10000:
        insights.append("Price requires caution because revenue has not been validated.")
    if not insights:
        insights.append("Opportunity depends on diligence around traffic quality, churn, and seller claims.")

    return insights


def portfolio_observations(listings: list[Listing]) -> list[str]:
    observations: list[str] = []
    if not listings:
        return ["No listings available yet."]

    top = max(listings, key=lambda listing: listing.bend_score or 0)
    observations.append(f"Highest overall opportunity is {top.title} at {top.bend_score:.0f}/100.")

    under_monetized = [
        listing for listing in listings if listing.traffic_estimate >= 10000 and listing.monthly_revenue < 500
    ]
    if under_monetized:
        observations.append(f"{len(under_monetized)} businesses have meaningful traffic but weak monetization.")

    profitable = [listing for listing in listings if listing.monthly_profit > 0]
    attractive = [
        listing for listing in profitable if (revenue_multiple(listing) or 999) <= 18
    ]
    if attractive:
        observations.append(f"{len(attractive)} profitable businesses have attractive revenue multiples.")

    category_counts: dict[str, int] = {}
    for listing in listings:
        category_counts[listing.category] = category_counts.get(listing.category, 0) + 1
    strongest_category = max(category_counts, key=category_counts.get)
    observations.append(f"Largest category in the database is {strongest_category}.")

    return observations

