from __future__ import annotations

import logging
import time

from bend_score.analysis.insights import portfolio_observations
from bend_score.collectors.sample_data import sample_listings
from bend_score.config import SEED_COUNT
from bend_score.database.repository import ListingRepository
from bend_score.logging_utils import configure_logging
from bend_score.recommendations import apply_recommendation
from bend_score.reports.markdown import write_reports
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

        listings = refresh_scores(repository, logger)
        ranked = sorted(listings, key=lambda item: item.bend_score or 0, reverse=True)
        latest_path, dated_path = write_reports(ranked, repository.list_watchlist())
        logger.info("reports generated latest=%s dated=%s", latest_path, dated_path)

        ui.header()
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


def _ready_repository() -> ListingRepository:
    repository = ListingRepository()
    repository.create_schema()
    if repository.count() == 0:
        repository.add_many(sample_listings()[:SEED_COUNT])
    refresh_scores(repository)
    return repository
