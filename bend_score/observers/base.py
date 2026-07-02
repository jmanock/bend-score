from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from bend_score.models import Signal


@dataclass
class ObserverResult:
    observer: str
    label: str
    raw_count: int
    signals: list[Signal]
    runtime_seconds: float


class Observer(ABC):
    name: str = ""
    label: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "name", ""):
            return
        from bend_score.observers.registry import ObserverRegistry

        ObserverRegistry.register(cls)

    def run(self) -> ObserverResult:
        started = time.perf_counter()
        raw_items = self.collect()
        signals = self.normalize(raw_items)
        return ObserverResult(
            observer=self.name,
            label=self.label or self.name,
            raw_count=len(raw_items),
            signals=signals,
            runtime_seconds=time.perf_counter() - started,
        )

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        """Collect raw facts from a source."""

    @abstractmethod
    def normalize(self, raw_items: list[dict[str, Any]]) -> list[Signal]:
        """Normalize raw facts into standard Signal objects."""
