from __future__ import annotations

import re
from pathlib import Path

from bend_score.config import REPORT_DIR
from bend_score.models import Listing


BLUEPRINT_DIR = REPORT_DIR / "project_blueprints"


def write_project_blueprints(
    listings: list[Listing],
    blueprint_dir: Path = BLUEPRINT_DIR,
    limit: int = 10,
) -> list[Path]:
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    ranked = sorted(
        listings,
        key=lambda listing: ((listing.founder_score or 0), (listing.portfolio_fit or 0), (listing.bend_score or 0)),
        reverse=True,
    )
    paths: list[Path] = []
    for listing in ranked[:limit]:
        path = blueprint_dir / f"{_slug(listing.title)}.md"
        path.write_text(build_project_blueprint(listing), encoding="utf-8")
        paths.append(path)
    return paths


def build_project_blueprint(listing: Listing) -> str:
    project_name = _project_name(listing)
    audience = _target_audience(listing)
    revenue_model = _revenue_model(listing)
    stack = _tech_stack(listing)
    apis = _apis(listing)
    database = _database(listing)
    automation = _automation_opportunities(listing)
    seo = _seo_strategy(listing)
    affiliates = _affiliate_networks(listing)
    content = _content_ideas(listing)
    mobile = _mobile_ideas(listing)
    roadmap = _roadmap(listing)

    return "\n".join(
        [
            f"# {project_name} Blueprint",
            "",
            f"Source listing: {listing.title}",
            f"Recommendation: {listing.recommendation or 'n/a'}",
            f"Bend Score: {(listing.bend_score or 0):.0f}/100",
            f"Founder Score: {(listing.founder_score or 0):.0f}/100",
            f"Portfolio Fit: {(listing.portfolio_fit or 0):.0f}/100",
            "",
            "## Elevator Pitch",
            "",
            _elevator_pitch(listing),
            "",
            "## Target Audience",
            "",
            audience,
            "",
            "## Revenue Model",
            "",
            revenue_model,
            "",
            "## Suggested Tech Stack",
            "",
            stack,
            "",
            "## Suggested APIs",
            "",
            apis,
            "",
            "## Database",
            "",
            database,
            "",
            "## Automation Opportunities",
            "",
            automation,
            "",
            "## SEO Strategy",
            "",
            seo,
            "",
            "## Affiliate Networks",
            "",
            affiliates,
            "",
            "## Content Ideas",
            "",
            content,
            "",
            "## Future Mobile App Ideas",
            "",
            mobile,
            "",
            "## Expansion Roadmap",
            "",
            roadmap,
            "",
            "## Estimated MVP Timeline",
            "",
            listing.build_complexity or "Small (1 week)",
            "",
            "## Estimated Monthly Maintenance",
            "",
            listing.maintenance_estimate or "Medium: monthly analytics, content, and monetization checks.",
            "",
        ]
    )


def _project_name(listing: Listing) -> str:
    title = listing.title.replace(".com", "").replace(".io", "")
    if "blog" in listing.category.lower() or "content" in listing.category.lower():
        return f"{title} Intelligence Hub"
    if "saas" in listing.category.lower():
        return f"{title} OS"
    return title


def _elevator_pitch(listing: Listing) -> str:
    if _has_any(listing, ["florida", "travel", "routes", "hotels", "cruise"]):
        return f"A practical Florida-focused discovery product that turns {listing.title} into a searchable planning and deal engine."
    if _has_any(listing, ["affiliate", "comparison", "review", "deals"]):
        return f"A focused affiliate intelligence site that helps buyers compare options and surfaces high-intent offers from {listing.title}."
    if _has_any(listing, ["saas", "plugin", "extension", "crm", "tracker"]):
        return f"A lightweight productized workflow tool that improves the core job already proven by {listing.title}."
    return f"A focused opportunity platform built around the existing asset, audience, and search demand behind {listing.title}."


def _target_audience(listing: Listing) -> str:
    if _has_any(listing, ["wedding"]):
        return "Wedding planners and small event operators who need simple client, lead, and timeline workflows."
    if _has_any(listing, ["florida", "travel", "kayak", "routes"]):
        return "Florida travelers, locals planning weekends, and visitors comparing trip options."
    if _has_any(listing, ["shopify", "woocommerce"]):
        return "Small ecommerce operators who want practical automation without enterprise software."
    if _has_any(listing, ["developer", "dev", "github"]):
        return "Indie developers, technical founders, and small software teams."
    return f"People actively searching for {listing.category.lower()} solutions and alternatives."


def _revenue_model(listing: Listing) -> str:
    models = []
    if listing.monthly_revenue > 0:
        models.append("preserve current revenue first")
    if _has_any(listing, ["saas", "plugin", "extension", "crm", "tracker"]):
        models.append("monthly subscriptions")
        models.append("paid upgrades")
    if _has_any(listing, ["affiliate", "deals", "travel", "gear", "comparison", "reviews"]):
        models.append("affiliate commissions")
    if _has_any(listing, ["newsletter", "content", "directory", "blog"]):
        models.append("sponsorships and newsletter placements")
    if not models:
        models.append("lead generation and paid templates")
    return "- " + "\n- ".join(dict.fromkeys(models))


def _tech_stack(listing: Listing) -> str:
    existing = listing.tech_stack.strip() or "Existing stack unknown"
    return (
        f"- Start from existing stack: {existing}\n"
        "- Add a small Next.js or Python admin layer only if it accelerates content, scoring, or workflow automation.\n"
        "- Keep analytics, email capture, and affiliate link tracking simple in V1."
    )


def _apis(listing: Listing) -> str:
    apis = []
    if _has_any(listing, ["stripe", "subscription", "saas"]):
        apis.append("Stripe")
    if _has_any(listing, ["shopify"]):
        apis.append("Shopify")
    if _has_any(listing, ["github", "developer"]):
        apis.append("GitHub")
    if _has_any(listing, ["newsletter", "beehiiv"]):
        apis.append("Beehiiv or email service provider")
    if _has_any(listing, ["travel", "florida", "hotel", "flight", "cruise"]):
        apis.append("affiliate travel/search partners where available")
    if not apis:
        apis.append("No required API for MVP; start with owned data and manual curation")
    return "- " + "\n- ".join(dict.fromkeys(apis))


def _database(listing: Listing) -> str:
    if _has_any(listing, ["directory", "city pages", "routes", "local"]):
        return "PostgreSQL or SQLite for structured location, category, page, and affiliate records."
    if _has_any(listing, ["saas", "plugin", "extension"]):
        return "PostgreSQL for accounts, billing state, product events, and audit logs."
    return "SQLite is enough for V1; migrate to PostgreSQL when workflow or publishing volume grows."


def _automation_opportunities(listing: Listing) -> str:
    ideas = [
        "Generate recurring opportunity briefs for Morning Content.",
        "Track stale pages, missing affiliate links, and conversion gaps.",
    ]
    if _has_any(listing, ["directory", "content", "blog", "routes"]):
        ideas.append("Generate page briefs by city, category, route, or comparison cluster.")
    if _has_any(listing, ["saas", "plugin", "extension"]):
        ideas.append("Automate onboarding emails, churn checks, product analytics, and support triage.")
    return "- " + "\n- ".join(ideas)


def _seo_strategy(listing: Listing) -> str:
    if _has_any(listing, ["florida", "local", "routes", "directory"]):
        return "- Build city/category pages.\n- Add comparison pages.\n- Refresh seasonal pages monthly.\n- Connect winners to Florida Deals Network."
    if _has_any(listing, ["affiliate", "comparison", "reviews"]):
        return "- Expand comparison keywords.\n- Add alternatives pages.\n- Improve review depth and offer freshness."
    return "- Start with use-case pages, alternatives pages, and integration pages tied to buyer-intent searches."


def _affiliate_networks(listing: Listing) -> str:
    networks = []
    if _has_any(listing, ["travel", "florida", "hotel", "flight", "cruise", "gear"]):
        networks.extend(["Travel affiliate partners", "AWIN", "Impact", "CJ"])
    if _has_any(listing, ["software", "saas", "developer", "tools", "plugin"]):
        networks.extend(["PartnerStack", "Impact", "direct SaaS partner programs"])
    if _has_any(listing, ["amazon", "chair", "gear"]):
        networks.append("Amazon Associates")
    if not networks:
        networks.append("Direct partner outreach after traffic validation")
    return "- " + "\n- ".join(dict.fromkeys(networks))


def _content_ideas(listing: Listing) -> str:
    base = [
        f"Best {listing.category.lower()} options for beginners",
        f"{listing.title} alternatives and comparisons",
        f"How to evaluate {listing.category.lower()} tools before buying",
    ]
    if _has_any(listing, ["florida", "local", "travel"]):
        base.extend(["Florida city guides", "Weekend itinerary posts", "Seasonal deal roundups"])
    return "- " + "\n- ".join(base)


def _mobile_ideas(listing: Listing) -> str:
    if _has_any(listing, ["mobile app", "tracker", "routes", "courts", "travel"]):
        return "- Saved places or saved opportunities\n- Push reminders for updates\n- Lightweight trip or task checklist"
    return "- Saved searches\n- Alerts for new opportunities\n- Mobile-friendly dashboard before a native app"


def _roadmap(listing: Listing) -> str:
    return (
        "- Week 1: preserve current asset, analytics, and core conversion paths.\n"
        "- Month 1: publish first SEO/content clusters and add email capture.\n"
        "- Month 3: add automation, affiliate experiments, and portfolio cross-promotion.\n"
        "- Month 6: decide whether to expand into SaaS, mobile, or a larger content/data platform."
    )


def _has_any(listing: Listing, needles: list[str]) -> bool:
    text = f"{listing.title} {listing.category} {listing.description} {listing.seller_notes} {listing.tech_stack}".lower()
    return any(needle in text for needle in needles)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "opportunity"
