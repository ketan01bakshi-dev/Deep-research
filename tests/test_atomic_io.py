"""Atomic JSON I/O tests."""

from __future__ import annotations

import json

from agent_core.io import atomic_write_text, save_json


def test_save_json_round_trip(tmp_path):
    path = tmp_path / "data.json"
    save_json(path, {"count": 3, "name": "test"})
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == {"count": 3, "name": "test"}


def test_atomic_write_text_overwrites(tmp_path):
    path = tmp_path / "counter.txt"
    atomic_write_text(path, "first")
    atomic_write_text(path, "second")
    assert path.read_text(encoding="utf-8") == "second"
