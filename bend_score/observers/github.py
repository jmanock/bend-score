from __future__ import annotations

from typing import Any

from bend_score.models import Signal
from bend_score.observers.base import Observer


class GitHubObserver(Observer):
    name = "github"
    label = "GitHub Observer"

    def collect(self) -> list[dict[str, Any]]:
        return []

    def normalize(self, raw_items: list[dict[str, Any]]) -> list[Signal]:
        return []
