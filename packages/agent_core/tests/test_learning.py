from __future__ import annotations

from agent_core.learning import bump_weight, decay_weights, top_keys


def test_decay_weights_drops_small_values() -> None:
    result = decay_weights({"keep": 1.0, "drop": 0.04}, decay=0.97, floor=0.05)
    assert "keep" in result
    assert "drop" not in result


def test_bump_weight_accumulates() -> None:
    weights: dict[str, float] = {}
    bump_weight(weights, "python", 2.0)
    bump_weight(weights, "python", 1.0)
    assert weights["python"] == 3.0


def test_top_keys_orders_by_weight() -> None:
    weights = {"a": 1.0, "b": 5.0, "c": 3.0}
    assert top_keys(weights, 2) == ["b", "c"]
