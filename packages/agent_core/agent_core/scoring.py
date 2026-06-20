"""Weighted scoring framework."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScoreSignal:
    name: str
    weight: float
    value: float  # 0..1


def weighted_score(signals: list[ScoreSignal]) -> tuple[float, dict[str, float]]:
    total = sum(signal.value * signal.weight for signal in signals)
    breakdown = {signal.name: round(signal.value * signal.weight, 1) for signal in signals}
    return round(min(100.0, total), 1), breakdown


def partition_by_threshold(
    items: list[dict[str, Any]],
    score_key: str,
    min_score: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    above = [item for item in items if item.get(score_key, 0) >= min_score]
    below = [item for item in items if item.get(score_key, 0) < min_score]
    return above, below
