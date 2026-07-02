# Bend Score

Bend Score is an offline, terminal-first acquisition intelligence tool for digital businesses and neglected online assets.

It helps evaluate SaaS products, content sites, newsletters, Chrome extensions, mobile apps, domains, affiliate sites, WordPress plugins, and other small digital assets. Bend Score stores listings in SQLite, scores them with modular rule-based scorers, ranks opportunities, manages a watchlist, and generates markdown acquisition reports.

V2 is still intentionally private and local. There is no scraping, no paid API, no OpenAI or LLM dependency, no authentication, no cloud service, and no web dashboard.

## Install

```bash
cd /Users/jonmanock/Documents/Codex/bend-score
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

V2 uses only the Python standard library.

## Run

```bash
python main.py run
```

This creates the database if needed, seeds sample listings when empty, recalculates scores, prints a polished terminal intelligence report, writes logs, and generates:

- `reports/latest.md`
- `reports/YYYY-MM-DD.md`

## Commands

```bash
python main.py run
python main.py top
python main.py stats
python main.py search saas
python main.py search newsletter
python main.py search affiliate
python main.py watch 4
python main.py watchlist
python main.py note 4 "Check seller history and traffic quality"
```

## Architecture

```text
bend_score/
  analysis/              Rule-based business observations
  ai/                    Placeholder for future AI-assisted ideas
  collectors/            Sample data now, future marketplace collectors later
  database/              SQLite repository and watchlist persistence
  reports/               Markdown report generation
  scoring/               Modular acquisition scoring engines
  app.py                 Command workflows
  config.py              Paths, logging folders, seed count, scoring weights
  models.py              Listing and watchlist models
  recommendations.py     BUY / WATCH / RESEARCH / PASS assignment
  ui.py                  Terminal formatting
data/                    Local SQLite database
logs/                    Daily run logs
reports/                 Generated markdown reports
tests/                   Unit tests
```

## Scoring

Each listing is evaluated by modular scorers in `bend_score/scoring/`.

Each scorer returns:

```python
{
    "score": 0-10,
    "explanation": "...",
    "confidence": 0-100,
}
```

The current V2 scorers are:

- acquisition score
- automation score
- SEO score
- revenue score
- maintenance score
- AI leverage score
- competition score
- exit score

`bend_score/scoring/bend_score.py` combines those components into one 0-100 Bend Score using configurable weights from `bend_score/config.py`.

## Recommendations

Every listing receives one recommendation:

- `BUY`
- `RESEARCH`
- `WATCH`
- `PASS`

The recommendation includes a short explanation and is stored with the listing.

## Watchlists

The `watchlist` SQLite table tracks listings you want to monitor.

Statuses supported by the database:

- Watching
- Researching
- Interested
- Contacted
- Passed
- Purchased

Use:

```bash
python main.py watch 4
python main.py note 4 "Review Chrome Web Store reviews"
python main.py watchlist
```

## Reports

Reports include:

- top opportunities
- highest revenue
- highest ROI potential
- most automation potential
- best SEO opportunities
- businesses added today
- watchlist summary
- interesting observations

## Logging

Every `run` writes to a daily log file in `logs/`.

Example:

```text
logs/2026-07-02.log
```

Logs include database setup, seed completion, score calculation, report generation, runtime, and errors when they occur.

## Future Collectors

Bend Score is designed to add real collectors later for:

- Flippa
- Acquire.com
- Microns
- Empire Flippers
- GitHub
- Product Hunt
- Reddit
- newsletters

Collectors should normalize external records into the existing `Listing` model before scoring.

## Future AI

The `bend_score/ai/` folder is reserved for future optional AI assistance, such as diligence summaries, buyer questions, or opportunity memos. V2 does not call any AI APIs.

## Test

```bash
python3 -m unittest discover
```
