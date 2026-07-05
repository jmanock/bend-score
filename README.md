# Bend Score

Bend Score is a terminal-first opportunity intelligence platform for finding, evaluating, and planning digital acquisition or build opportunities.

V7.5 adds Consensus Intelligence on top of Opportunity Memory, Founder Intelligence, the observer framework, marketplace intake, Bend Score scoring, reports, recommendations, watchlist workflow, SQLite timeline, Observer Pack foundation, GitHub intelligence, and Morning Content Engine signal export. Instead of treating every observer signal as isolated, Bend Score now merges related signals into consensus opportunities with heat, observer agreement, and portfolio allocation.

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
- `reports/project_blueprints/*.md`

Daily logs are stored in:

- `logs/YYYY-MM-DD.log`

## Commands

```bash
python3 main.py run
python3 main.py top
python3 main.py top3
python3 main.py consensus
python3 main.py heat
python3 main.py stats
python3 main.py search saas
python3 main.py watch 4
python3 main.py watchlist
python3 main.py note 4 "Check seller history and traffic quality"
python3 main.py github
python3 main.py observers
python3 main.py observer github
python3 main.py signals
python3 main.py signals github
python3 main.py import-csv examples/sample_listings.csv
python3 main.py add-listing
python3 main.py listings
python3 main.py listing 21
python3 main.py opportunity 21
python3 main.py feedback 21 love "Good fit for automation and SEO"
python3 main.py export-signals
python3 main.py signals-outbox
```

## Architecture

```text
Observer -> Raw Facts -> Signal -> SQLite Timeline -> Founder Intelligence -> Opportunity Memory -> Consensus Intelligence -> Morning Investment Memo
```

```text
bend_score/
  core/                  Observer orchestration and intelligence runs
  observers/             Observer base class, registry, fake observer, GitHub observer
  models/                Listing, watchlist, and standardized Signal models
  database/              SQLite repository, listings, watchlist, signals, signal history
  reports/               Markdown intelligence briefings and project blueprints
  intelligence/          Consensus merging, heat scoring, top-three selection, allocation analysis
  intake/                CSV/manual listing validation and normalization
  utils/                 Confidence and config helpers
  scoring/               Bend Score and Founder Score engines
  analysis/              Rule-based business insights
  ai/                    Placeholder only; no paid API or AI calls
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
  project_blueprints/    Build/acquisition blueprints for top opportunities
  opportunity_history/   Optional JSON exports of score and recommendation memory
tests/
  unit tests
signals/
  outbox/                Morning Content Engine signal JSON exports
  archive/               Optional storage for handled exported signals
```

## Morning Content Engine Signal Export

V7.5 exports high-value Bend Score opportunities as standardized signal JSON files for Morning Content Engine, now with consensus metadata when available.

Run:

```bash
python3 main.py export-signals
python3 main.py signals-outbox
```

Signals are written to:

```text
signals/outbox/
```

Consensus-backed exports include:

- `consensus_score`
- `heat_score`
- `observer_count`
- `observer_names`
- `consensus_fingerprint`
- `consensus_market`
- `consensus_keywords`

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
- or recommendation contains `BUILD NOW`, `ACQUIRE`, `BUILD LATER`, `WATCH`, or `RESEARCH`
- or confidence is `80` or higher

`IGNORE` and `PASS` items are not exported.

Each signal metadata object includes:

- original listing id
- Bend Score
- Founder Score
- Portfolio Fit
- recommendation
- build complexity
- maintenance estimate
- revenue timeline
- executive summary
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

Bend Score supports two no-scraping intake paths:

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

## Observer Pack 1.0

Observer Pack 1.0 lives in `bend_score/observers/packs/`.

Planned observers:

- GitHub
- Product Hunt
- Hacker News
- Reddit
- Google Trends
- WordPress Plugins
- Chrome Extensions

V7 implements GitHub improvements only. It uses the public GitHub REST API, supports optional `GITHUB_TOKEN`, and continues with public rate limits when no token is present.

GitHub intelligence detects:

- fast-growing repositories
- abandoned popular repositories
- repos with many issues
- AI, automation, and developer tooling projects
- projects with no website/homepage
- commercial potential
- founder-profile matches

Strong GitHub signals are converted into normal Bend Score opportunities. They receive Bend Score, Founder Score, Portfolio Fit, Build Complexity, maintenance estimates, recommendations, memory, blueprints, and Morning Content signal export metadata.

Editable GitHub query families live in `config/observers.yaml`, including AI tools, automation tools, developer tools, abandoned popular repos, business tools, marketing tools, Chrome extensions, and no-homepage tools.

## Consensus Intelligence

Consensus Intelligence lives in `bend_score/intelligence/consensus.py`.

It builds deterministic opportunity fingerprints from:

- title similarity
- normalized keywords
- tags and topics
- category
- source
- language

No embeddings or paid APIs are required. The goal is simple, repeatable matching across observers. When GitHub, future Google Trends, Reddit, Product Hunt, or other observers point at the same market or problem, Bend Score groups them into a single consensus opportunity.

Consensus opportunities receive:

- Consensus Score, based on observer count, Founder Score, Bend Score, trend, Portfolio Fit, recommendation agreement, and confidence
- Heat Score, based on independent observer agreement around the same market, keyword, category, or problem
- observer agreement details
- portfolio allocation recommendations by market
- Top 3 reasoning that favors consensus and heat, not only raw score
- executive recommendation: Build, Watch, Ignore

CLI commands:

```bash
python3 main.py consensus
python3 main.py top3
python3 main.py heat
```

## Intelligence Reports

`reports/latest.md` is now a daily intelligence briefing with:

- Consensus Opportunities
- Today's Top 3
- Observer Agreement
- Heat Rankings
- Portfolio Allocation
- Executive Recommendation
- Founder Score
- Portfolio Fit
- Build Complexity
- Maintenance
- Revenue Timeline
- Executive Summary
- GitHub Intelligence, when GitHub is enabled

## Founder Intelligence

Founder Intelligence is separate from Bend Score. Bend Score evaluates the asset as a business listing. Founder Score evaluates whether the opportunity fits Jon's build, automation, content, affiliate, SEO, and portfolio strategy.

Founder Score considers:

- automation potential
- API availability
- SEO scalability
- affiliate potential
- evergreen demand
- content generation potential
- ability to create hundreds or thousands of pages
- monthly maintenance effort
- competition level
- recurring revenue potential
- SaaS or mobile app expansion
- cross-promotion with Florida Deals, Offer Radar, Morning Content, and Morning OS-style workflows
- ease of MVP
- long-term defensibility

Recommendations use the V6 action labels:

- `★★★★★ BUILD NOW`
- `★★★★☆ ACQUIRE`
- `★★★★☆ BUILD LATER`
- `★★★☆☆ WATCH`
- `★★☆☆☆ RESEARCH`
- `★☆☆☆☆ IGNORE`

Every top opportunity in `reports/latest.md` includes the Founder Score, Portfolio Fit, build complexity, maintenance estimate, revenue timeline, and an executive summary. The same run also writes project blueprints into `reports/project_blueprints/` with target audience, revenue model, tech stack, APIs, database, automation opportunities, SEO strategy, affiliate networks, content ideas, mobile ideas, roadmap, MVP timeline, and monthly maintenance.

## Opportunity Memory

Every `python3 main.py run` stores an opportunity snapshot in SQLite and exports optional JSON history files into `reports/opportunity_history/`.

Tracked memory includes:

- first seen and last seen
- title, category, and source
- current Bend Score and Founder Score
- current recommendation
- historical Bend Scores
- historical Founder Scores
- recommendation history
- times seen
- notes

Trend labels are calculated from recent score history:

- `NEW`
- `RISING`
- `FALLING`
- `STABLE`
- `VOLATILE`

Use the detail command to inspect one opportunity:

```bash
python3 main.py opportunity 21
```

The detail view shows current scores, trend, recommendation, score history, feedback history, blueprint path, and next action.

## Founder Feedback

Store lightweight founder feedback with:

```bash
python3 main.py feedback 21 love "Good fit for automation and SEO"
```

Allowed reactions:

- `love`
- `like`
- `ignore`
- `build`
- `buy`
- `pass`
- `research`

Feedback is stored in SQLite. Loved or build/buy categories get a small future boost. Ignored or passed categories get a small penalty, especially when similar opportunities have higher maintenance. Adjustments are intentionally small and are included in recommendation explanations when they apply.

## Morning Memo Sections

`reports/latest.md` is intentionally concise and includes:

- Executive Summary
- Today's Top 3 Opportunities
- Today's Movers
- Opportunity Clusters
- Suggested Build Roadmap
- Feedback Notes
- Full Opportunity Table

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
