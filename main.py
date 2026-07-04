from __future__ import annotations

import argparse

from bend_score import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Bend Score digital asset scouting tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="Generate today's acquisition intelligence report.")
    subparsers.add_parser("top", help="Show the highest scoring businesses.")
    subparsers.add_parser("stats", help="Show portfolio analytics.")
    subparsers.add_parser("watchlist", help="Show watchlist items.")
    subparsers.add_parser("github", help="Run only the GitHub observer.")
    subparsers.add_parser("add-listing", help="Manually add a listing through terminal prompts.")
    subparsers.add_parser("listings", help="Show recent listings.")
    subparsers.add_parser("export-signals", help="Export high-value opportunities to signals/outbox.")
    subparsers.add_parser("signals-outbox", help="List current Morning Content Engine signal files.")

    import_parser = subparsers.add_parser("import-csv", help="Import marketplace listings from CSV.")
    import_parser.add_argument("path")

    listing_parser = subparsers.add_parser("listing", help="Show full detail for one listing.")
    listing_parser.add_argument("listing_id", type=int)

    signals_parser = subparsers.add_parser("signals", help="Show recent signals.")
    signals_parser.add_argument("observer", nargs="?")

    search_parser = subparsers.add_parser("search", help="Search listings by keyword.")
    search_parser.add_argument("query")

    watch_parser = subparsers.add_parser("watch", help="Add a listing to the watchlist.")
    watch_parser.add_argument("listing_id", type=int)

    note_parser = subparsers.add_parser("note", help="Add a note to a watched listing.")
    note_parser.add_argument("listing_id", type=int)
    note_parser.add_argument("text")

    args = parser.parse_args()

    if args.command == "run":
        app.run()
    elif args.command == "top":
        app.top()
    elif args.command == "stats":
        app.stats()
    elif args.command == "search":
        app.search(args.query)
    elif args.command == "watch":
        app.watch(args.listing_id)
    elif args.command == "watchlist":
        app.watchlist()
    elif args.command == "note":
        app.note(args.listing_id, args.text)
    elif args.command == "github":
        app.github()
    elif args.command == "signals":
        app.signals(args.observer)
    elif args.command == "import-csv":
        app.import_csv(args.path)
    elif args.command == "add-listing":
        app.add_listing()
    elif args.command == "listings":
        app.listings()
    elif args.command == "listing":
        app.listing_detail(args.listing_id)
    elif args.command == "export-signals":
        app.export_signals()
    elif args.command == "signals-outbox":
        app.signals_outbox()


if __name__ == "__main__":
    main()
