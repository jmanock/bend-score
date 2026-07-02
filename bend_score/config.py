from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "bend_score.sqlite3"
REPORT_DIR = BASE_DIR / "reports"
LOG_DIR = BASE_DIR / "logs"
OBSERVER_CONFIG_PATH = BASE_DIR / "config" / "observers.yaml"
SEED_COUNT = 15

DEFAULT_SCORING_WEIGHTS = {
    "acquisition": 1.4,
    "automation": 1.1,
    "seo": 1.2,
    "revenue": 1.4,
    "maintenance": 0.9,
    "ai_leverage": 0.8,
    "competition": 0.8,
    "exit": 1.0,
}
