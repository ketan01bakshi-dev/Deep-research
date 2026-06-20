"""Decay-weight learning primitives."""

from __future__ import annotations


def decay_weights(
    weights: dict[str, float],
    *,
    decay: float = 0.97,
    floor: float = 0.05,
) -> dict[str, float]:
    return {k: round(v * decay, 4) for k, v in weights.items() if v * decay >= floor}


def bump_weight(weights: dict[str, float], key: str, delta: float = 1.0) -> None:
    weights[key] = weights.get(key, 0) + delta


def top_keys(weights: dict[str, float], n: int = 10) -> list[str]:
    return [k for k, _ in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:n]]
