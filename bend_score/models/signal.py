from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from bend_score.models.listing import utc_now


RECOMMENDATIONS = {"BUY", "BUILD", "WATCH", "RESEARCH", "IGNORE"}
IMPACTS = {"low", "medium", "high"}


@dataclass
class Signal:
    id: int | None
    timestamp: str
    observer: str
    signal_type: str
    title: str
    description: str
    category: str
    confidence: int
    impact: str
    recommendation: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = max(0, min(100, int(self.confidence)))
        self.impact = self.impact.lower()
        if self.impact not in IMPACTS:
            self.impact = "medium"
        self.recommendation = normalize_recommendation(self.recommendation)

    @classmethod
    def create(
        cls,
        observer: str,
        signal_type: str,
        title: str,
        description: str,
        category: str,
        confidence: int,
        impact: str,
        recommendation: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Signal":
        return cls(
            id=None,
            timestamp=utc_now(),
            observer=observer,
            signal_type=signal_type,
            title=title,
            description=description,
            category=category,
            confidence=confidence,
            impact=impact,
            recommendation=recommendation,
            metadata=metadata or {},
        )

    @classmethod
    def from_row(cls, row: Any) -> "Signal":
        return cls(
            id=row["id"],
            timestamp=row["timestamp"],
            observer=row["observer"],
            signal_type=row["signal_type"],
            title=row["title"],
            description=row["description"],
            category=row["category"],
            confidence=row["confidence"],
            impact=row["impact"],
            recommendation=row["recommendation"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def metadata_json(self) -> str:
        return json.dumps(self.metadata, sort_keys=True)


def normalize_recommendation(value: str) -> str:
    normalized = value.strip().upper()
    mapping = {
        "INVESTIGATE": "RESEARCH",
        "PASS": "IGNORE",
        "CONTACT": "RESEARCH",
        "PURCHASE": "BUY",
        "MONITOR": "WATCH",
    }
    normalized = mapping.get(normalized, normalized)
    return normalized if normalized in RECOMMENDATIONS else "RESEARCH"
