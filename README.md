# Bend Score

Bend Score is a terminal-first internet intelligence platform for finding and evaluating digital acquisition opportunities.

V5 adds Morning Content Engine signal export on top of the observer, marketplace intake, scoring, reports, recommendations, and watchlist workflow. You can paste or import real listings, score them, and export the best opportunities as standardized signal JSON files.

Bend Score uses GitHub's public REST API for the GitHub Observer. It does not use paid APIs, OpenAI calls, marketplace scraping, cloud services, authentication, or a web dashboard.

## Run

```bash
python3 main.py run
```

You should see:

```text
Loading observers...
✓ Fake Opportunity Observer
✓ GitHub Observer
Collected:
15 opportunities
90 repositories
Generated:
hundreds of signals
Highest Confidence:
95%
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
python3 main.py github
python3 main.py signals
python3 main.py signals github
python3 main.py import-csv examples/sample_listings.csv
python3 main.py add-listing
python3 main.py listings
python3 main.py listing 21
python3 main.py export-signals
python3 main.py signals-outbox
```

## Architecture

```text
Observer -> Raw Facts -> Signal -> SQLite Timeline -> Intelligence Report
```

```text
bend_score/
  core/                  Observer orchestration and intelligence runs
  observers/             Observer base class, registry, fake observer, GitHub observer
  models/                Listing, watchlist, and standardized Signal models
  database/              SQLite repository, listings, watchlist, signals, signal history
  reports/               Markdown intelligence briefings
  intake/                CSV/manual listing validation and normalization
  utils/                 Confidence and config helpers
  scoring/               Existing Bend Score acquisition scoring
  analysis/              Rule-based business insights
  ai/                    Placeholder only; no AI calls in V5
examples/
  sample_listings.csv    Example marketplace listing import file
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
signals/
  outbox/                Morning Content Engine signal JSON exports
  archive/               Optional storage for handled exported signals
```

## Morning Content Engine Signal Export

V5 can export high-value Bend Score opportunities as standardized signal JSON files for Morning Content Engine.

Run:

```bash
python3 main.py export-signals
python3 main.py signals-outbox
```

Signals are written to:

```text
signals/outbox/
```

The exporter uses the Morning Content Engine Signal Contract:

- `source_project`: `bend-score`
- `source_type`: `opportunity`
- `brand`: `Bend Score`
- `title`
- `summary`
- `url`
- `category`: `business-opportunity`
- `priority`
- `confidence`
- `tags`
- `metadata`

Export selection rules:

- Bend Score is `70` or higher
- or recommendation is `BUY`, `BUILD`, `WATCH`, or `RESEARCH`
- or confidence is `80` or higher

`IGNORE` and `PASS` items are not exported.

Each signal metadata object includes:

- original listing id
- Bend Score
- recommendation
- asking price
- monthly revenue
- monthly profit
- source
- category
- score breakdown

Filenames are stable per listing/source/date, so running export repeatedly on the same day will not create duplicates.

Example workflow:

```bash
cd ~/Documents/Codex/bend-score
python3 main.py run
python3 main.py export-signals

cd ~/Documents/Codex/morning-content-engine
python main.py collect-signals
python main.py morning
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

## Manual Intake

V5 supports two no-scraping intake paths:

```bash
python3 main.py import-csv examples/sample_listings.csv
python3 main.py add-listing
```

Imported and manually added listings are normalized, validated, scored, stored in SQLite, and included in:

- `python3 main.py run`
- `python3 main.py top`
- `python3 main.py stats`
- `python3 main.py listings`
- `reports/latest.md`

### CSV Format

Expected CSV columns:

```text
title
url
source
category
asking_price
monthly_revenue
monthly_profit
traffic_estimate
description
seller_notes
tech_stack
```

Missing optional fields are allowed. Numeric fields may include commas or dollar signs. URL is optional, but if present it must start with `http://` or `https://`.

Supported source names:

- Flippa
- Acquire
- Microns
- Empire Flippers
- FE International
- Motion Invest
- Manual
- Other

Unknown sources are normalized to `Other`.

### Import Report

After importing, Bend Score prints:

- rows processed
- rows imported
- duplicates skipped
- errors
- highest scoring imported listing

Duplicates are detected by normalized title + URL.

### Listing Views

Use:

```bash
python3 main.py listings
python3 main.py listing <id>
```

`listings` shows recent listings with ID, title, source, category, asking price, revenue, profit, and Bend Score.

`listing <id>` shows all listing fields, score breakdown, recommendation, improvement ideas, and watchlist status.

### Sample Workflow

```bash
python3 main.py import-csv examples/sample_listings.csv
python3 main.py listings
python3 main.py top
python3 main.py listing 21
python3 main.py run
```

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
  enabled: true
  queries:
    developer_tools:
      enabled: true
      query: "stars:>500 language:Python pushed:>2025-01-01"
    ai_tools:
      enabled: true
      query: "AI stars:>1000 pushed:>2025-01-01"
    automation:
      enabled: true
      query: "automation stars:>300 pushed:>2025-01-01"
    abandoned_popular:
      enabled: true
      query: "stars:>1000 pushed:<2024-01-01"
    chrome_extensions:
      enabled: true
      query: "chrome extension stars:>200"

reddit:
  enabled: false
```

## GitHub Observer

V4 adds the first real internet-connected observer:

- `GitHub Observer`

The GitHub Observer searches public repositories for developer tools, AI tools, automation projects, abandoned popular repos, and Chrome extension opportunities. It collects repository metadata such as stars, forks, issues, language, license, topics, homepage, owner, created date, pushed date, archive status, and default branch.

It generates rule-based signals such as:

- `github_fast_growth_candidate`
- `github_abandoned_popular_repo`
- `github_commercial_potential`
- `github_developer_tool`
- `github_ai_tool`
- `github_automation_tool`
- `github_high_issue_demand`
- `github_no_homepage_opportunity`

Use:

```bash
python3 main.py github
python3 main.py signals github
```

### GitHub Token

`GITHUB_TOKEN` is optional. Without it, the observer still works through unauthenticated public API requests, but GitHub rate limits are lower.

Add a token to your shell or `.env` workflow:

```bash
export GITHUB_TOKEN="your_token_here"
```

`.env.example` includes the variable name for reference.

## Fake Opportunity Observer

V4 keeps the reference fake observer:

- `Fake Opportunity Observer`

It converts the existing sample opportunity generator into normalized signals. This preserves the V1/V2 demo data while proving the observer framework.

## Future Observer Examples

Future observers can plug into the same architecture:

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
- GitHub Intelligence, when GitHub is enabled

The GitHub section includes:

- Fast Growth Candidates
- Abandoned Popular Repos
- Commercial Potential
- AI / Automation Tools
- No Homepage Opportunities
- High Issue Demand

## Limitations

- GitHub search results are limited by public API rate limits.
- Signals are heuristics, not acquisition advice.
- The observer does not scrape repository websites or marketplaces.
- Same-day duplicate GitHub signals for the same repo and signal type are skipped.
- No private repository access is used.

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
