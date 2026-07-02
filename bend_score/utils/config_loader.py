from __future__ import annotations

from pathlib import Path


def load_observer_config(path: Path) -> dict[str, dict[str, bool]]:
    if not path.exists():
        return {}

    config: dict[str, dict[str, bool]] = {}
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not raw_line.startswith(" ") and line.endswith(":"):
            current = line[:-1]
            config[current] = {}
            continue
        if current and ":" in line:
            key, value = [part.strip() for part in line.split(":", 1)]
            config[current][key] = value.lower() in {"true", "yes", "1", "on"}
    return config

