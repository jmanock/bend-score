from __future__ import annotations

from dataclasses import dataclass

from bend_score.models import Listing
from bend_score.scoring.common import combined_text


FACTOR_WEIGHTS: dict[str, int] = {
    "automation_potential": 10,
    "api_availability": 8,
    "seo_scalability": 9,
    "affiliate_potential": 8,
    "evergreen_demand": 8,
    "content_generation_potential": 7,
    "thousands_of_pages": 7,
    "low_maintenance_effort": 8,
    "low_competition": 6,
    "recurring_revenue_potential": 7,
    "saas_or_mobile_expansion": 6,
    "cross_promotion": 6,
    "portfolio_fit": 7,
    "ease_of_mvp": 7,
    "long_term_defensibility": 6,
}


@dataclass(frozen=True)
class FounderScoreResult:
    total: float
    factors: dict[str, dict[str, object]]
    reasons: list[str]


@dataclass(frozen=True)
class PortfolioFitResult:
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class ComplexityResult:
    label: str
    explanation: str
    maintenance: str


@dataclass(frozen=True)
class TimelineResult:
    label: str
    explanation: str


@dataclass(frozen=True)
class FounderIntelligence:
    founder_score: FounderScoreResult
    portfolio_fit: PortfolioFitResult
    complexity: ComplexityResult
    revenue_timeline: TimelineResult
    recommendation: str
    recommendation_explanation: str
    executive_summary: str


def calculate_founder_score(listing: Listing) -> FounderScoreResult:
    factor_scores = {
        "automation_potential": _automation_potential(listing),
        "api_availability": _api_availability(listing),
        "seo_scalability": _seo_scalability(listing),
        "affiliate_potential": _affiliate_potential(listing),
        "evergreen_demand": _evergreen_demand(listing),
        "content_generation_potential": _content_generation_potential(listing),
        "thousands_of_pages": _thousands_of_pages(listing),
        "low_maintenance_effort": _low_maintenance_effort(listing),
        "low_competition": _low_competition(listing),
        "recurring_revenue_potential": _recurring_revenue_potential(listing),
        "saas_or_mobile_expansion": _saas_or_mobile_expansion(listing),
        "cross_promotion": _cross_promotion(listing),
        "portfolio_fit": _portfolio_fit_points(listing),
        "ease_of_mvp": _ease_of_mvp(listing),
        "long_term_defensibility": _long_term_defensibility(listing),
    }
    total_weight = sum(FACTOR_WEIGHTS.values())
    total = round(
        sum(score * FACTOR_WEIGHTS[name] for name, (score, _reason) in factor_scores.items()) / total_weight,
        1,
    )
    factors = {
        name: {
            "score": score,
            "weight": FACTOR_WEIGHTS[name],
            "reason": reason,
        }
        for name, (score, reason) in factor_scores.items()
    }
    reasons = _top_reasons(factors)
    return FounderScoreResult(total=total, factors=factors, reasons=reasons)


def calculate_portfolio_fit(listing: Listing) -> PortfolioFitResult:
    text = combined_text(listing)
    score = 35
    reasons: list[str] = []

    if _has_any(text, ["florida", "travel", "hotel", "flight", "cruise", "local", "outdoor", "fishing"]):
        score += 22
        reasons.append("Complements Florida Deals through travel, local, or outdoor content.")
    if _has_any(text, ["affiliate", "deal", "coupon", "comparison", "review", "cashback", "credit"]):
        score += 18
        reasons.append("Can feed Offer Radar or affiliate-led deal content.")
    if _has_any(text, ["newsletter", "content", "directory", "blog", "seo", "city pages", "comparison"]):
        score += 15
        reasons.append("Can supply Morning Content with recurring post ideas.")
    if _has_any(text, ["automation", "api", "stripe", "github", "database", "saas", "plugin", "extension"]):
        score += 12
        reasons.append("Fits Morning OS-style automation and workflow tooling.")
    if listing.traffic_estimate >= 10000:
        score += 8
        reasons.append("Existing audience can feed other portfolio properties.")
    if listing.monthly_revenue > 0 or listing.monthly_profit > 0:
        score += 5
        reasons.append("Existing monetization reduces cold-start risk.")

    if not reasons:
        reasons.append("Loose portfolio fit; would need a clearer connection to existing projects.")

    return PortfolioFitResult(score=min(100, round(score, 1)), reasons=reasons)


def estimate_build_complexity(listing: Listing) -> ComplexityResult:
    text = combined_text(listing)
    category = listing.category.lower()
    effort = 1
    reasons: list[str] = []

    if "domain" in category:
        reasons.append("Domain-only opportunity mainly needs landing pages and validation.")
    elif _has_any(category, ["content", "affiliate", "newsletter"]):
        effort += 1
        reasons.append("Content or newsletter build can start with templates and editorial workflow.")
    elif _has_any(category, ["extension", "plugin"]):
        effort += 2
        reasons.append("Extension or plugin requires product polish, docs, and release packaging.")
    elif _has_any(category, ["saas", "mobile"]):
        effort += 3
        reasons.append("Product opportunity requires auth, billing, onboarding, and support flows.")

    if _has_any(text, ["stripe", "api", "firebase", "postgres", "mysql", "rails", "django", "laravel"]):
        effort += 1
        reasons.append("Existing app stack adds integration and maintenance work.")
    if _has_any(text, ["clunky", "outdated", "weak docs", "bare", "dated"]):
        effort += 1
        reasons.append("Visible product debt needs cleanup before scaling.")
    if listing.monthly_revenue > 1000:
        effort += 1
        reasons.append("Revenue is meaningful enough to require careful migration and QA.")

    if effort <= 1:
        label = "Tiny (1-2 days)"
    elif effort <= 2:
        label = "Small (1 week)"
    elif effort <= 4:
        label = "Medium (2-4 weeks)"
    elif effort <= 6:
        label = "Large"
    else:
        label = "Massive"

    maintenance = estimate_maintenance(listing)
    return ComplexityResult(label=label, explanation=" ".join(reasons), maintenance=maintenance)


def estimate_maintenance(listing: Listing) -> str:
    text = combined_text(listing)
    if _has_any(text, ["support volume is low", "domain only", "static", "webflow", "wordpress"]):
        return "Low: a few hours per month for updates, affiliate checks, and content refreshes."
    if _has_any(text, ["saas", "stripe", "plugin", "extension", "firebase", "rails", "django", "laravel"]):
        return "Medium: weekly product, support, dependency, and billing checks."
    if _has_any(text, ["mobile app", "ios", "android", "retention", "paywall"]):
        return "Medium-high: app store upkeep, analytics, support, and release testing."
    return "Medium: monthly content, analytics, and monetization maintenance."


def estimate_revenue_timeline(listing: Listing) -> TimelineResult:
    text = combined_text(listing)
    if listing.monthly_revenue > 0:
        return TimelineResult(
            label="1 month",
            explanation="Revenue already exists, so the first month can focus on preserving conversion and adding quick monetization wins.",
        )
    if listing.traffic_estimate >= 10000 and _has_any(text, ["affiliate", "content", "directory", "blog", "comparison"]):
        return TimelineResult(
            label="3 months",
            explanation="Traffic exists but monetization needs affiliate offers, email capture, and conversion testing.",
        )
    if _has_any(text, ["domain", "parked", "never launched"]):
        return TimelineResult(
            label="6 months",
            explanation="The asset needs a useful MVP, early content, and first distribution loops before revenue is realistic.",
        )
    return TimelineResult(
        label="6 months",
        explanation="Assumes a focused MVP, SEO/content launch, and several months of audience building before material revenue.",
    )


def founder_recommendation(
    bend_score: float,
    founder_score: float,
    portfolio_fit: float,
    complexity: str,
    maintenance: str,
) -> tuple[str, str]:
    complexity_penalty = 12 if complexity in {"Large", "Massive"} else 0
    maintenance_penalty = 6 if "high" in maintenance.lower() else 0
    blended = (bend_score * 0.38) + (founder_score * 0.42) + (portfolio_fit * 0.20) - complexity_penalty - maintenance_penalty

    if blended >= 82 and founder_score >= 78 and portfolio_fit >= 70 and complexity not in {"Large", "Massive"}:
        return "★★★★★ BUILD NOW", "High Founder Score, strong portfolio fit, and manageable build complexity make this worth immediate action."
    if bend_score >= 78 and listing_ready_for_acquisition_score(founder_score, portfolio_fit):
        return "★★★★☆ ACQUIRE", "The asset has acquisition value and enough founder upside to justify diligence."
    if blended >= 70:
        return "★★★★☆ BUILD LATER", "Good strategic fit, but timing or execution effort suggests staging it behind stronger opportunities."
    if blended >= 58:
        return "★★★☆☆ WATCH", "There are useful signals, but proof, price, or portfolio leverage needs to improve."
    if blended >= 45:
        return "★★☆☆☆ RESEARCH", "Interesting enough for diligence, but not enough evidence for build or acquisition work yet."
    return "★☆☆☆☆ IGNORE", "The opportunity has weak fit, weak founder leverage, or too much execution drag."


def listing_ready_for_acquisition_score(founder_score: float, portfolio_fit: float) -> bool:
    return founder_score >= 65 and portfolio_fit >= 55


def executive_summary_for(
    listing: Listing,
    recommendation: str,
    founder_score: float,
    portfolio_fit: float,
    complexity: str,
    timeline: str,
) -> str:
    action = recommendation.split(" ", 1)[-1] if " " in recommendation else recommendation
    opening = "This is an excellent long-term opportunity." if founder_score >= 80 else "This is a useful opportunity, but it needs disciplined validation."
    if recommendation.endswith("IGNORE"):
        opening = "This is not a strong fit for the current portfolio."
    return (
        f"{opening} Founder Score is {founder_score:.0f}/100 and Portfolio Fit is {portfolio_fit:.0f}/100. "
        f"The build is estimated as {complexity}, with likely revenue movement in {timeline}. "
        f"Recommended action: {action}."
    )


def analyze_founder_intelligence(listing: Listing, bend_score: float) -> FounderIntelligence:
    founder = calculate_founder_score(listing)
    portfolio = calculate_portfolio_fit(listing)
    complexity = estimate_build_complexity(listing)
    timeline = estimate_revenue_timeline(listing)
    recommendation, explanation = founder_recommendation(
        bend_score,
        founder.total,
        portfolio.score,
        complexity.label,
        complexity.maintenance,
    )
    summary = executive_summary_for(
        listing,
        recommendation,
        founder.total,
        portfolio.score,
        complexity.label,
        timeline.label,
    )
    return FounderIntelligence(
        founder_score=founder,
        portfolio_fit=portfolio,
        complexity=complexity,
        revenue_timeline=timeline,
        recommendation=recommendation,
        recommendation_explanation=explanation,
        executive_summary=summary,
    )


def _top_reasons(factors: dict[str, dict[str, object]]) -> list[str]:
    labels = {
        "automation_potential": "Automation potential is strong.",
        "api_availability": "APIs or integration hooks are available.",
        "seo_scalability": "SEO expansion can create many durable pages.",
        "affiliate_potential": "Affiliate or partner programs can support monetization.",
        "evergreen_demand": "Demand is evergreen instead of news-driven.",
        "content_generation_potential": "The niche can generate repeatable content ideas.",
        "thousands_of_pages": "The data model can expand into hundreds or thousands of pages.",
        "low_maintenance_effort": "Maintenance burden looks manageable.",
        "low_competition": "Competition appears manageable for a focused niche angle.",
        "recurring_revenue_potential": "Recurring revenue is plausible.",
        "saas_or_mobile_expansion": "The opportunity can evolve into SaaS, mobile, or tooling.",
        "cross_promotion": "It can cross-promote with existing projects.",
        "portfolio_fit": "It fits the current portfolio thesis.",
        "ease_of_mvp": "An MVP can be shipped quickly.",
        "long_term_defensibility": "The asset can build defensibility through data, workflows, or audience.",
    }
    ranked = sorted(factors.items(), key=lambda item: (item[1]["score"], item[1]["weight"]), reverse=True)
    return [labels[name] for name, factor in ranked if int(factor["score"]) >= 75][:9]


def _automation_potential(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["automation", "api", "stripe", "sidekiq", "firebase", "github", "workflow"]):
        return 90, "Stack or workflow has clear automation hooks."
    if _has_any(text, ["directory", "content", "wordpress", "newsletter"]):
        return 72, "Publishing and refresh workflows can be automated."
    return 50, "Automation path is not obvious from the listing."


def _api_availability(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["api", "stripe", "github", "firebase", "shopify", "chrome", "woocommerce", "freemius"]):
        return 90, "Known platforms or APIs are present."
    if _has_any(text, ["wordpress", "airtable", "beehiiv", "webflow", "gumroad"]):
        return 74, "CMS or creator-platform integrations are available."
    return 45, "No obvious API surface is mentioned."


def _seo_scalability(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if listing.traffic_estimate >= 15000 or _has_any(text, ["directory", "city pages", "comparison", "local seo", "rank"]):
        return 92, "Existing traffic or directory structure suggests scalable SEO."
    if _has_any(text, ["content", "blog", "newsletter", "templates"]):
        return 76, "Content angles can support search growth."
    return 48, "SEO scale is unproven."


def _affiliate_potential(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["affiliate", "amazon", "comparison", "reviews", "deal", "coupon", "travel", "gear"]):
        return 90, "Affiliate monetization is directly relevant."
    if _has_any(text, ["newsletter", "directory", "content", "templates"]):
        return 68, "Affiliate offers could be layered into the audience."
    return 42, "Affiliate path is not obvious."


def _evergreen_demand(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["templates", "crm", "plugin", "extension", "bookkeepers", "courts", "routes", "deals", "tracker"]):
        return 86, "The topic solves repeatable evergreen needs."
    if _has_any(text, ["weekly", "newsletter", "meeting notes"]):
        return 72, "Demand is durable but requires ongoing freshness."
    return 58, "Evergreen demand needs more evidence."


def _content_generation_potential(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["directory", "content", "blog", "newsletter", "comparison", "templates", "local", "routes"]):
        return 92, "The niche supports repeatable guides, comparisons, and updates."
    if _has_any(text, ["saas", "plugin", "extension", "mobile app"]):
        return 66, "Product education and use cases can create content."
    return 45, "Content surface is limited."


def _thousands_of_pages(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["directory", "city pages", "local", "routes", "templates", "comparison keywords"]):
        return 93, "The concept can expand by city, category, route, or template."
    if _has_any(text, ["content", "blog", "affiliate site"]):
        return 72, "The site can grow through programmatic or editorial page clusters."
    return 38, "Page-scale expansion is limited."


def _low_maintenance_effort(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["domain only", "support volume is low", "static", "templates", "webflow"]):
        return 88, "Operations look light after launch."
    if _has_any(text, ["saas", "mobile", "plugin", "extension", "support", "firebase"]):
        return 55, "Product/support upkeep is real but manageable."
    return 70, "Maintenance appears moderate."


def _low_competition(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["local", "niche", "exact-match", "tiny", "small"]):
        return 78, "Niche positioning may avoid broad-market competition."
    if _has_any(text, ["crowded", "ai meeting", "macro tracker", "chair deals"]):
        return 40, "Competitive category requires a sharper wedge."
    return 60, "Competition level is unclear."


def _recurring_revenue_potential(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if listing.monthly_revenue > 0 and _has_any(text, ["stripe", "subscription", "saas", "plugin", "freemius"]):
        return 90, "Recurring billing or software revenue already exists."
    if _has_any(text, ["newsletter", "sponsors", "membership", "templates"]):
        return 70, "Recurring sponsorship, membership, or product revenue is plausible."
    if listing.monthly_revenue > 0:
        return 62, "Revenue exists, but recurrence is unclear."
    return 35, "Recurring revenue is not yet proven."


def _saas_or_mobile_expansion(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["saas", "mobile app", "plugin", "extension", "crm", "tracker", "finder"]):
        return 92, "The asset can become or already is a product."
    if _has_any(text, ["directory", "templates", "tools", "calculator"]):
        return 70, "There is a path into tools or lightweight SaaS."
    return 42, "SaaS or mobile extension path is weak."


def _cross_promotion(listing: Listing) -> tuple[int, str]:
    portfolio = calculate_portfolio_fit(listing)
    if portfolio.score >= 80:
        return 92, "Multiple current projects can send or receive traffic."
    if portfolio.score >= 60:
        return 72, "At least one current project can support distribution."
    return 42, "Cross-promotion path is limited."


def _portfolio_fit_points(listing: Listing) -> tuple[int, str]:
    portfolio = calculate_portfolio_fit(listing)
    return int(portfolio.score), "; ".join(portfolio.reasons)


def _ease_of_mvp(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["domain only", "templates", "content", "directory", "newsletter", "wordpress", "webflow"]):
        return 86, "A first useful version can be launched with content, templates, or simple data."
    if _has_any(text, ["saas", "plugin", "extension"]):
        return 62, "MVP is feasible but requires product work."
    if _has_any(text, ["mobile app", "ios", "android"]):
        return 45, "Mobile MVP requires app-store and release overhead."
    return 58, "MVP path is possible but not obvious."


def _long_term_defensibility(listing: Listing) -> tuple[int, str]:
    text = combined_text(listing)
    if _has_any(text, ["loyal customers", "data", "directory", "reviews", "subscribers", "local seo", "workflow"]):
        return 82, "Audience, data, workflow, or local footprint can compound."
    if listing.traffic_estimate >= 10000:
        return 70, "Search footprint can become a durable acquisition channel."
    return 45, "Defensibility needs to be built from scratch."


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)
