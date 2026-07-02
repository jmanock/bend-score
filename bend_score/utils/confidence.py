from __future__ import annotations


def clamp_confidence(value: int | float) -> int:
    return max(0, min(100, int(round(value))))


def weighted_confidence(parts: list[tuple[int | float, int | float]]) -> int:
    total_weight = sum(weight for _, weight in parts)
    if total_weight <= 0:
        return 0
    return clamp_confidence(sum(value * weight for value, weight in parts) / total_weight)


def confidence_reason(confidence: int, reasons: list[str]) -> str:
    prefix = "High confidence" if confidence >= 80 else "Medium confidence" if confidence >= 55 else "Low confidence"
    return f"{prefix}: " + "; ".join(reasons)

