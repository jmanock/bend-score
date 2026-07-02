# Bend Score

Bend Score is an offline, terminal-first internet intelligence platform for finding and evaluating digital acquisition opportunities.

V3 is built around **Observers** and **Signals**. Observers collect facts from a source. Signals normalize those facts into one standard intelligence format. The database stores every signal snapshot so Bend Score can build a timeline of opportunity intelligence over time.

No real scraping, APIs, OpenAI calls, cloud services, authentication, or web dashboard are included in V3.

## Run

```bash
python3 main.py run
```

You should see:

```text
Loading observers...
✓ Fake Opportunity Observer
Collected:
15 opportunities
Generated:
35 signals
Highest Confidence:
88%
Writing report...
Done.
```

Reports are generated at:

- `reports/latest.md`
- `reports/YYYY-MM-DD.md`

Daily logs are stored in:

- `logs/YYYY-MM-DD.log`

## Commands

```bash
python3 main.py run
python3 main.py top
python3 main.py stats
python3 main.py search saas
python3 main.py watch 4
python3 main.py watchlist
python3 main.py note 4 "Check seller history and traffic quality"
```

## Architecture

```text
Observer -> Raw Facts -> Signal -> SQLite Timeline -> Intelligence Report
```

```text
bend_score/
  core/                  Observer orchestration and intelligence runs
  observers/             Observer base class, registry, fake observer, future source stubs
  models/                Listing, watchlist, and standardized Signal models
  database/              SQLite repository, listings, watchlist, signals, signal history
  reports/               Markdown intelligence briefings
  utils/                 Confidence and config helpers
  scoring/               Existing Bend Score acquisition scoring
  analysis/              Rule-based business insights
  ai/                    Placeholder only; no AI calls in V3
config/
  observers.yaml         Enable or disable observers without code edits
data/
  bend_score.sqlite3     Local SQLite database
logs/
  YYYY-MM-DD.log         Run logs
reports/
  latest.md              Current daily briefing
tests/
  unit tests
```

## Observer Lifecycle

Every observer implements the same interface:

```python
name
run()
collect()
normalize()
```

- `collect()` gathers raw facts from a source.
- `normalize()` converts those facts into standard `Signal` objects.
- `run()` measures runtime and returns a normalized observer result.

Observers do not know anything about scoring. They only collect facts and normalize them.

New observers register automatically by subclassing `Observer` and setting a unique `name`.

## Signal Lifecycle

Every observer outputs the same `Signal` model:

```python
id
timestamp
observer
signal_type
title
description
category
confidence
impact
recommendation
metadata
```

Recommendations are standardized to:

- `BUY`
- `BUILD`
- `WATCH`
- `RESEARCH`
- `IGNORE`

Metadata is arbitrary JSON so future observers can store source-specific context without changing the core schema.

## Database Overview

SQLite remains the source of truth.

Current tables:

- `listings`
- `watchlist`
- `signals`
- `signal_history`

Every run inserts new rows into `signals` and `signal_history`. History is never overwritten. This creates the timeline Bend Score will later use for acceleration, trend, and anomaly detection.

## Observer Configuration

Enable or disable observers in:

```text
config/observers.yaml
```

Example:

```yaml
fake_opportunity:
  enabled: true

github:
  enabled: false

reddit:
  enabled: false
```

## Current Observer

V3 includes one real reference observer:

- `Fake Opportunity Observer`

It converts the existing sample opportunity generator into normalized signals. This preserves the V1/V2 demo data while proving the V3 observer framework.

## Future Observer Examples

Future observers can plug into the same architecture:

- GitHub repository growth
- Reddit niche demand
- Product Hunt launches
- Google Trends movement
- Acquire.com listings
- Flippa listings
- domains and expired domains
- newsletter marketplace signals

A small observer should be possible in under 100 lines because it only needs to collect facts and normalize them into `Signal` objects.

## Intelligence Reports

`reports/latest.md` is now a daily intelligence briefing with:

- High Confidence Signals
- BUY
- WATCH
- BUILD
- RESEARCH
- IGNORE
- Signal Summary
- Statistics
- Observer Summary
- Recommendations

## Roadmap

- Detect signal acceleration across `signal_history`
- Add source-specific observers one at a time
- Add duplicate and entity resolution
- Add richer confidence weighting
- Add local import/export workflows
- Add optional AI-generated diligence memos later
- Add a dashboard only after the terminal workflow is mature

## Test

```bash
python3 -m unittest discover
```
