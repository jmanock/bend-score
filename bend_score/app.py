from __future__ import annotations

import logging
import time
from pathlib import Path

from bend_score.analysis.insights import portfolio_observations
from bend_score.collectors.sample_data import sample_listings
from bend_score.config import SEED_COUNT
from bend_score.core.intelligence import run_observers
from bend_score.database.repository import ListingRepository
from bend_score.exporters.morning_content import SIGNAL_OUTBOX, export_opportunities
from bend_score.intake.github_opportunities import github_signals_to_listings
from bend_score.intake.listings import ImportResult, listing_from_mapping, load_csv_rows
from bend_score.intelligence.consensus import (
    build_consensus,
    executive_recommendation,
    heat_rankings,
    portfolio_allocation,
    top_three_consensus,
)
from bend_score.logging_utils import configure_logging
from bend_score.memory import (
    build_roadmap,
    detect_clusters,
    movers_for,
    next_action_for,
    trend_for_memory,
    write_opportunity_history_exports,
)
from bend_score.observers.github import GitHubObserver
from bend_score.observers.registry import ObserverRegistry
from bend_score.recommendations import apply_recommendation
from bend_score.reports.blueprints import write_project_blueprints
from bend_score.reports.markdown import write_intelligence_reports
from bend_score import ui


def run() -> None:
    start = time.perf_counter()
    logger = configure_logging()
    try:
        repository = ListingRepository()
        repository.create_schema()
        logger.info("database created")

        if repository.count() == 0:
            repository.add_many(sample_listings()[:SEED_COUNT])
            logger.info("seed completed count=%s", SEED_COUNT)

        print("Loading observers...")
        intelligence = run_observers()
        for result in intelligence.observer_results:
            print(f"{ui.GREEN}✓{ui.RESET} {result.label}")

        inserted_signals = repository.insert_signals(intelligence.signals)
        converted = add_github_opportunities(repository, intelligence.signals)
        logger.info("signals generated count=%s", len(intelligence.signals))
        logger.info("timeline updated count=%s", len(inserted_signals))
        logger.info("github opportunities converted count=%s", len(converted))

        listings = refresh_scores(repository, logger)
        memory_records = repository.record_opportunity_memory(listings)
        feedback_entries = repository.list_feedback()
        write_opportunity_history_exports(memory_records)
        ranked = sorted(listings, key=lambda item: item.bend_score or 0, reverse=True)
        consensus_opportunities = build_consensus(ranked, intelligence.signals, memory_records)
        print("Writing report...")
        blueprint_paths = write_project_blueprints(ranked)
        latest_path, dated_path = write_intelligence_reports(
            intelligence,
            repository.list_signals(limit=500),
            ranked,
            repository.list_watchlist(),
            memory_records=memory_records,
            feedback_entries=feedback_entries,
            clusters=detect_clusters(ranked),
            roadmap=build_roadmap(ranked, memory_records, feedback_entries),
            movers=movers_for(memory_records),
        )
        print("Done.")
        logger.info("reports generated latest=%s dated=%s", latest_path, dated_path)
        logger.info("project blueprints generated count=%s", len(blueprint_paths))

        ui.header()
        ui.section("Observer Run")
        print(f"{ui.GREEN}✓{ui.RESET} Observer loaded")
        print(f"{ui.GREEN}✓{ui.RESET} Signals generated: {len(intelligence.signals)}")
        print(f"{ui.GREEN}✓{ui.RESET} Timeline updated: {len(inserted_signals)} new snapshots")
        print(f"{ui.GREEN}✓{ui.RESET} GitHub opportunities converted: {len(converted)}")
        print(f"{ui.GREEN}✓{ui.RESET} Confidence calculated: {intelligence.average_confidence:.1f}% average")
        print(f"{ui.GREEN}✓{ui.RESET} Intelligence report generated")

        ui.section("Collected")
        for result in intelligence.observer_results:
            print(f"{result.raw_count} opportunities from {result.label}")

        ui.section("Generated")
        print(f"{len(intelligence.signals)} signals")
        print(f"{len(inserted_signals)} new timeline snapshots")
        print(f"Highest Confidence: {intelligence.highest_confidence}%")

        ui.section("Top Opportunities")
        print_consensus(top_three_consensus(consensus_opportunities), limit=3)

        ui.section("Watchlist Summary")
        ui.print_watchlist(repository.list_watchlist())

        ui.section("Statistics")
        ui.print_stats(repository.stats())

        ui.section("Recent Activity")
        print(f"Reports generated: {latest_path} and {dated_path}")
        print(f"Project blueprints generated: {len(blueprint_paths)}")
        for observation in portfolio_observations(ranked)[:3]:
            print(f"- {observation}")
        print(f"{ui.CYAN}================================={ui.RESET}")

        runtime = time.perf_counter() - start
        logger.info("runtime %.3fs", runtime)
    except Exception:
        logger.exception("errors")
        raise


def refresh_scores(repository: ListingRepository, logger: logging.Logger | None = None) -> list:
    listings = repository.list_all()
    feedback_entries = repository.list_feedback()
    for listing in listings:
        apply_recommendation(listing, feedback_entries)
    repository.update_scores(listings)
    if logger:
        logger.info("scores calculated count=%s", len(listings))
    return repository.list_all()


def add_github_opportunities(repository: ListingRepository, signals) -> list:
    converted = []
    for listing in github_signals_to_listings(signals):
        if repository.is_duplicate_listing(listing):
            continue
        converted.append(repository.add_listing(listing))
    return converted


def top(limit: int = 10) -> None:
    repository = _ready_repository()
    ui.header("Top Opportunities")
    ui.print_listings(repository.top(limit), limit=limit)


def consensus() -> None:
    repository = _ready_repository()
    opportunities = build_consensus(
        repository.list_all(),
        repository.list_signals(limit=500),
        repository.list_opportunity_memory(),
    )
    ui.header("Consensus Intelligence")
    print_consensus(opportunities, limit=10)
    ui.section("Portfolio Allocation")
    for item in portfolio_allocation(opportunities):
        print(f"{item.market}: {item.status} ({item.count} opportunities, heat {item.average_heat:.1f}/10)")
        print(f"  Recommendation: {item.recommendation}")
    ui.section("Executive Recommendation")
    for line in executive_recommendation(opportunities).values():
        print(f"- {line}")


def top3() -> None:
    repository = _ready_repository()
    opportunities = top_three_consensus(
        build_consensus(repository.list_all(), repository.list_signals(limit=500), repository.list_opportunity_memory())
    )
    ui.header("Today's Top 3")
    print_consensus(opportunities, limit=3)


def heat() -> None:
    repository = _ready_repository()
    opportunities = heat_rankings(
        build_consensus(repository.list_all(), repository.list_signals(limit=500), repository.list_opportunity_memory())
    )
    ui.header("Heat Rankings")
    for opportunity in opportunities[:10]:
        print(f"{opportunity.heat_score:.1f}/10  {opportunity.title}")
        for observer, score in opportunity.heat_by_observer.items():
            print(f"  {observer}: {score:.1f}/10")


def search(query: str) -> None:
    repository = _ready_repository()
    ui.header(f"Search: {query}")
    ui.print_listings(repository.search(query))


def stats() -> None:
    repository = _ready_repository()
    ui.header("Business Analytics")
    ui.print_stats(repository.stats())


def watch(listing_id: int) -> None:
    repository = _ready_repository()
    item = repository.add_to_watchlist(listing_id)
    listing = item.listing
    title = listing.title if listing else f"Listing #{listing_id}"
    print(f"Added #{listing_id} to watchlist: {title}")


def watchlist() -> None:
    repository = _ready_repository()
    ui.header("Watchlist")
    ui.print_watchlist(repository.list_watchlist())


def note(listing_id: int, text: str) -> None:
    repository = _ready_repository()
    item = repository.append_note(listing_id, text)
    title = item.listing.title if item.listing else f"Listing #{listing_id}"
    print(f"Added note to #{listing_id}: {title}")


def feedback(listing_id: int, reaction: str, note_text: str = "") -> None:
    allowed = {"love", "like", "ignore", "build", "buy", "pass", "research"}
    if reaction.lower() not in allowed:
        print(f"Invalid reaction: {reaction}. Allowed: {', '.join(sorted(allowed))}")
        return
    repository = _ready_repository()
    entry = repository.add_feedback(listing_id, reaction.lower(), note_text)
    refresh_scores(repository)
    listing = repository.get_listing(listing_id)
    ui.header("Founder Feedback")
    print(f"Stored feedback for #{listing_id}: {entry.reaction}")
    if note_text:
        print(f"Note: {note_text}")
    if listing:
        print(f"Updated Founder Score: {(listing.founder_score or 0):.1f}/100")
        print(f"Updated Recommendation: {listing.recommendation}")


def github() -> None:
    logger = configure_logging()
    repository = _ready_repository()
    enabled_names = {observer.name for observer in ObserverRegistry.enabled()}
    if "github" not in enabled_names:
        ui.header("GitHub Observer")
        print("GitHub Observer is disabled in config/observers.yaml.")
        print("Set github.enabled: true to run it.")
        return

    observer = GitHubObserver()
    print("Running GitHub Observer...")
    result = observer.run()
    inserted = repository.insert_signals(result.signals)
    converted = add_github_opportunities(repository, result.signals)
    if converted:
        refresh_scores(repository)
    logger.info("GitHub observer runtime %.3fs", result.runtime_seconds)
    logger.info("GitHub signals generated count=%s inserted=%s", len(result.signals), len(inserted))

    ui.header("GitHub Intelligence")
    print(f"Collected repositories: {result.raw_count}")
    print(f"Generated signals: {len(result.signals)}")
    print(f"Stored new signals: {len(inserted)}")
    print(f"Converted opportunities: {len(converted)}")
    print(f"Runtime: {result.runtime_seconds:.3f}s")
    if not observer.token:
        print("Warning: GITHUB_TOKEN is not set, so GitHub API rate limits are lower.")
    if observer.errors:
        print("Warnings:")
        for error in observer.errors:
            print(f"- {error}")
    ui.section("Recent GitHub Signals")
    preview = inserted[:25] if inserted else repository.list_signals(limit=25, observer="github")
    ui.print_signals(preview)


def observers() -> None:
    ui.header("Observers")
    enabled = {observer.name for observer in ObserverRegistry.enabled()}
    for name, observer_cls in sorted(ObserverRegistry.all().items()):
        state = "enabled" if name in enabled else "disabled"
        print(f"{name}: {observer_cls.label} ({state})")


def observer(name: str) -> None:
    if name == "github":
        github()
        return
    observers_map = ObserverRegistry.all()
    if name not in observers_map:
        print(f"Observer not found: {name}")
        return
    instance = observers_map[name]()
    print(f"Running {instance.label}...")
    result = instance.run()
    repository = _ready_repository()
    inserted = repository.insert_signals(result.signals)
    print(f"Collected: {result.raw_count}")
    print(f"Generated signals: {len(result.signals)}")
    print(f"Stored new signals: {len(inserted)}")


def signals(observer: str | None = None) -> None:
    repository = _ready_repository()
    ui.header("Signals" if not observer else f"Signals: {observer}")
    ui.print_signals(repository.list_signals(limit=25, observer=observer))


def import_csv(path: str) -> None:
    repository = _ready_repository()
    result = import_csv_file(Path(path), repository)
    ui.header("CSV Import")
    print(f"Rows processed: {result.rows_processed}")
    print(f"Rows imported: {len(result.imported)}")
    print(f"Duplicates skipped: {result.duplicates_skipped}")
    print(f"Errors: {len(result.errors)}")
    for error in result.errors:
        print(f"- {error}")
    if result.highest_scoring:
        listing = result.highest_scoring
        print(
            f"Highest scoring imported listing: #{listing.id} {listing.title} "
            f"({listing.bend_score:.1f}/100)"
        )
    else:
        print("Highest scoring imported listing: n/a")


def import_csv_file(path: Path, repository: ListingRepository) -> ImportResult:
    result = ImportResult()
    if not path.exists():
        result.errors.append(f"File not found: {path}")
        return result

    for row_number, row in enumerate(load_csv_rows(path), start=2):
        result.rows_processed += 1
        try:
            listing = listing_from_mapping(row)
        except ValueError as exc:
            result.errors.append(f"Row {row_number}: {exc}")
            continue
        if repository.is_duplicate_listing(listing):
            result.duplicates_skipped += 1
            continue
        result.imported.append(repository.add_listing(listing))
    return result


def add_listing() -> None:
    repository = _ready_repository()
    fields = [
        ("title", "Title"),
        ("url", "URL"),
        ("source", "Source"),
        ("category", "Category"),
        ("asking_price", "Asking price"),
        ("monthly_revenue", "Monthly revenue"),
        ("monthly_profit", "Monthly profit"),
        ("traffic_estimate", "Traffic estimate"),
        ("description", "Description"),
        ("seller_notes", "Notes"),
        ("tech_stack", "Tech stack"),
    ]
    data: dict[str, str] = {}
    for key, label in fields:
        data[key] = input(f"{label}: ")

    try:
        listing = create_manual_listing(data, repository)
    except ValueError as exc:
        print(f"Could not add listing: {exc}")
        return
    print(f"Added listing #{listing.id}: {listing.title} ({listing.bend_score:.1f}/100)")


def create_manual_listing(data: dict[str, object], repository: ListingRepository) -> object:
    listing = listing_from_mapping({**data, "source": data.get("source") or "Manual"})
    if repository.is_duplicate_listing(listing):
        raise ValueError("duplicate listing detected by title and URL.")
    return repository.add_listing(listing)


def listings() -> None:
    repository = _ready_repository()
    ui.header("Recent Listings")
    ui.print_recent_listings(repository.recent_listings())


def listing_detail(listing_id: int) -> None:
    repository = _ready_repository()
    listing = repository.get_listing(listing_id)
    if not listing:
        print(f"Listing #{listing_id} not found.")
        return
    ui.header(f"Listing #{listing_id}")
    ui.print_listing_detail(listing, repository.watchlist_status(listing_id))


def opportunity_detail(listing_id: int) -> None:
    repository = _ready_repository()
    listing = repository.get_listing(listing_id)
    if not listing:
        print(f"Opportunity #{listing_id} not found.")
        return
    memory = repository.get_opportunity_memory(listing_id)
    feedback_entries = repository.list_feedback(listing_id)
    trend = trend_for_memory(memory) if memory else None
    ui.header(f"Opportunity #{listing_id}")
    print(f"Title: {listing.title}")
    print(f"Category: {listing.category}")
    print(f"Source: {listing.source}")
    print(f"Bend Score: {(listing.bend_score or 0):.1f}/100")
    print(f"Founder Score: {(listing.founder_score or 0):.1f}/100")
    print(f"Portfolio Fit: {(listing.portfolio_fit or 0):.1f}/100")
    print(f"Trend: {trend.label if trend else 'NEW'}")
    if trend:
        print(f"Bend score change: {trend.bend_score_change:+.1f}")
        print(f"Founder score change: {trend.founder_score_change:+.1f}")
        print(f"Recommendation change: {trend.recommendation_change}")
        print(f"Times seen: {trend.times_seen}")
    print(f"Recommendation: {listing.recommendation}")
    print(f"Executive summary: {listing.executive_summary or 'n/a'}")
    print(f"Blueprint path: reports/project_blueprints/{_slug(listing.title)}.md")
    print(f"Next action: {next_action_for(listing)}")
    print()
    print("Score history:")
    if memory and memory.history:
        for snapshot in memory.history[-8:]:
            print(
                f"- {snapshot.timestamp}: Bend {snapshot.bend_score:.1f}, "
                f"Founder {snapshot.founder_score:.1f}, {snapshot.recommendation}"
            )
    else:
        print("- No history recorded yet. Run python3 main.py run to create memory.")
    print()
    print("Feedback history:")
    if feedback_entries:
        for entry in feedback_entries:
            suffix = f" - {entry.note}" if entry.note else ""
            print(f"- {entry.created_at}: {entry.reaction}{suffix}")
    else:
        print("- No feedback yet.")


def export_signals() -> None:
    repository = _ready_repository()
    listings = repository.list_all()
    memory_records = repository.list_opportunity_memory()
    consensus_metadata = {
        listing_id: metadata
        for opportunity in build_consensus(listings, repository.list_signals(limit=500), memory_records)
        for listing_id, metadata in [
            (
                listing.id,
                {
                    "consensus_score": round(opportunity.consensus_score, 1),
                    "heat_score": round(opportunity.heat_score, 1),
                    "observer_count": opportunity.observer_count,
                    "observer_names": opportunity.observers,
                    "consensus_fingerprint": opportunity.fingerprint,
                    "consensus_market": opportunity.market,
                    "consensus_keywords": opportunity.keywords,
                },
            )
            for listing in opportunity.listings
            if listing.id is not None
        ]
    }
    summary = export_opportunities(listings, memory_records=memory_records, consensus_metadata=consensus_metadata)
    ui.header("Morning Content Signal Export")
    for line in summary.lines():
        print(line)


def signals_outbox() -> None:
    SIGNAL_OUTBOX.mkdir(parents=True, exist_ok=True)
    files = sorted(SIGNAL_OUTBOX.glob("*.json"))
    ui.header("Signals Outbox")
    if not files:
        print("No signal files in signals/outbox.")
        return
    for path in files:
        print(path)


def _ready_repository() -> ListingRepository:
    repository = ListingRepository()
    repository.create_schema()
    if repository.count() == 0:
        repository.add_many(sample_listings()[:SEED_COUNT])
    refresh_scores(repository)
    return repository


def print_consensus(opportunities, limit: int = 10) -> None:
    if not opportunities:
        print("No consensus opportunities yet.")
        return
    for index, opportunity in enumerate(opportunities[:limit], start=1):
        listing = opportunity.primary_listing
        print(
            f"{index}. {opportunity.title} | Consensus {opportunity.consensus_score:.1f}/100 | "
            f"Heat {opportunity.heat_score:.1f}/10 | Observers {', '.join(opportunity.observers)}"
        )
        if listing:
            print(
                f"   Founder {(listing.founder_score or 0):.1f} | Bend {(listing.bend_score or 0):.1f} | "
                f"{listing.build_complexity or 'n/a'} | Revenue {listing.revenue_timeline or 'n/a'}"
            )
        for reason in opportunity.reasons[:2]:
            print(f"   - {reason}")


def _slug(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "opportunity"
