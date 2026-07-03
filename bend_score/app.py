from __future__ import annotations

import logging
import time

from bend_score.analysis.insights import portfolio_observations
from bend_score.collectors.sample_data import sample_listings
from bend_score.config import SEED_COUNT
from bend_score.core.intelligence import run_observers
from bend_score.database.repository import ListingRepository
from bend_score.logging_utils import configure_logging
from bend_score.observers.github import GitHubObserver
from bend_score.observers.registry import ObserverRegistry
from bend_score.recommendations import apply_recommendation
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
        logger.info("signals generated count=%s", len(intelligence.signals))
        logger.info("timeline updated count=%s", len(inserted_signals))

        listings = refresh_scores(repository, logger)
        ranked = sorted(listings, key=lambda item: item.bend_score or 0, reverse=True)
        print("Writing report...")
        latest_path, dated_path = write_intelligence_reports(
            intelligence,
            repository.list_signals(limit=500),
            ranked,
            repository.list_watchlist(),
        )
        print("Done.")
        logger.info("reports generated latest=%s dated=%s", latest_path, dated_path)

        ui.header()
        ui.section("Observer Run")
        print(f"{ui.GREEN}✓{ui.RESET} Observer loaded")
        print(f"{ui.GREEN}✓{ui.RESET} Signals generated: {len(intelligence.signals)}")
        print(f"{ui.GREEN}✓{ui.RESET} Timeline updated: {len(inserted_signals)} new snapshots")
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
        ui.print_listings(ranked, limit=10)

        ui.section("Watchlist Summary")
        ui.print_watchlist(repository.list_watchlist())

        ui.section("Statistics")
        ui.print_stats(repository.stats())

        ui.section("Recent Activity")
        print(f"Reports generated: {latest_path} and {dated_path}")
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
    for listing in listings:
        apply_recommendation(listing)
    repository.update_scores(listings)
    if logger:
        logger.info("scores calculated count=%s", len(listings))
    return repository.list_all()


def top(limit: int = 10) -> None:
    repository = _ready_repository()
    ui.header("Top Opportunities")
    ui.print_listings(repository.top(limit), limit=limit)


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
    logger.info("GitHub observer runtime %.3fs", result.runtime_seconds)
    logger.info("GitHub signals generated count=%s inserted=%s", len(result.signals), len(inserted))

    ui.header("GitHub Intelligence")
    print(f"Collected repositories: {result.raw_count}")
    print(f"Generated signals: {len(result.signals)}")
    print(f"Stored new signals: {len(inserted)}")
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


def signals(observer: str | None = None) -> None:
    repository = _ready_repository()
    ui.header("Signals" if not observer else f"Signals: {observer}")
    ui.print_signals(repository.list_signals(limit=25, observer=observer))


def _ready_repository() -> ListingRepository:
    repository = ListingRepository()
    repository.create_schema()
    if repository.count() == 0:
        repository.add_many(sample_listings()[:SEED_COUNT])
    refresh_scores(repository)
    return repository
