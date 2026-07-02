from __future__ import annotations

from bend_score.models import Listing


def why_interesting(listing: Listing) -> str:
    category = listing.category.lower()
    if listing.traffic_estimate >= 10000 and listing.monthly_revenue < 500:
        return "It already has attention, but the current monetization looks underbuilt."
    if listing.monthly_revenue >= 1000 and _has_weak_design_signal(listing):
        return "It has revenue proof and visible product/design upside."
    if category == "domain":
        return "It is a simple asset with positioning potential and low operating complexity."
    if listing.monthly_profit > 0 and listing.asking_price / max(listing.monthly_profit, 1) <= 18:
        return "The asking price looks reasonable relative to current profit."
    return "It has enough traction or fixable weakness to be worth a closer look."


def improvement_ideas(listing: Listing) -> list[str]:
    category = listing.category.lower()
    ideas: list[str] = []

    if category in {"content site", "affiliate site"} and listing.traffic_estimate > 5000 and listing.monthly_revenue < 500:
        ideas.append("Add higher-intent affiliate links, comparison tables, and email capture.")
    if category == "saas" and listing.monthly_revenue > 0 and _has_weak_design_signal(listing):
        ideas.append("Improve the landing page, onboarding flow, and in-app upgrade prompts.")
    if category == "newsletter" and listing.monthly_revenue == 0:
        ideas.append("Test sponsorship packages, affiliate offers, and a simple welcome sequence.")
    if category == "domain":
        ideas.append("Launch a focused landing page, collect leads, and validate the strongest niche angle.")
    if category == "mobile app" and listing.traffic_estimate > 1000 and listing.monthly_revenue < 1500:
        ideas.append("Test subscription pricing, lifecycle emails, and a clearer upgrade moment.")
    if category == "chrome extension":
        ideas.append("Create a sharper landing page and add a paid tier for power users.")
    if category == "wordpress plugin":
        ideas.append("Upgrade docs, settings UX, and lifecycle messaging for renewals.")
    if "directory" in _combined_text(listing):
        ideas.append("Expand programmatic pages around locations, alternatives, and use cases.")
    if "email" in _combined_text(listing) or "list" in _combined_text(listing):
        ideas.append("Build segmented email capture and automated follow-up campaigns.")

    if not ideas:
        ideas.append("Audit traffic sources, refresh positioning, and test one new monetization channel.")

    return ideas


def _combined_text(listing: Listing) -> str:
    return f"{listing.title} {listing.description} {listing.seller_notes}".lower()


def _has_weak_design_signal(listing: Listing) -> bool:
    text = _combined_text(listing)
    return any(word in text for word in ["dated", "plain", "clunky", "outdated", "bare", "weak design"])

