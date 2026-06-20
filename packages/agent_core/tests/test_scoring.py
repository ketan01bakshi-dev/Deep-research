from __future__ import annotations

from agent_core.scoring import ScoreSignal, partition_by_threshold, weighted_score


def test_weighted_score_caps_at_100() -> None:
    score, breakdown = weighted_score([ScoreSignal("a", 60, 1.0), ScoreSignal("b", 60, 1.0)])
    assert score == 100.0
    assert breakdown == {"a": 60.0, "b": 60.0}


def test_weighted_score_partial_signals() -> None:
    score, breakdown = weighted_score(
        [
            ScoreSignal("title", 23, 0.8),
            ScoreSignal("skills", 28, 0.5),
            ScoreSignal("location", 14, 1.0),
        ]
    )
    assert score == round(23 * 0.8 + 28 * 0.5 + 14 * 1.0, 1)
    assert breakdown["title"] == round(23 * 0.8, 1)


def test_partition_by_threshold() -> None:
    items = [{"match_score": 80}, {"match_score": 40}, {"match_score": 60}]
    above, below = partition_by_threshold(items, "match_score", 60)
    assert len(above) == 2
    assert len(below) == 1
    assert below[0]["match_score"] == 40
