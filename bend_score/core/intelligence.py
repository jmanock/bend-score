from __future__ import annotations

from dataclasses import dataclass

from bend_score.models import Signal
from bend_score.observers.base import ObserverResult
from bend_score.observers.registry import ObserverRegistry


@dataclass
class IntelligenceRun:
    observer_results: list[ObserverResult]
    signals: list[Signal]

    @property
    def observers_run(self) -> int:
        return len(self.observer_results)

    @property
    def signals_generated(self) -> int:
        return len(self.signals)

    @property
    def average_confidence(self) -> float:
        if not self.signals:
            return 0.0
        return sum(signal.confidence for signal in self.signals) / len(self.signals)

    @property
    def highest_confidence(self) -> int:
        return max([signal.confidence for signal in self.signals], default=0)


def run_observers() -> IntelligenceRun:
    results = [observer.run() for observer in ObserverRegistry.enabled()]
    signals = [signal for result in results for signal in result.signals]
    return IntelligenceRun(observer_results=results, signals=signals)

