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


if __name__ == "__main__":
    main()
