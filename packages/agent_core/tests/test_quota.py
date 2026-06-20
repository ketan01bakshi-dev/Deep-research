from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from agent_core.quota import DailyQuota


def test_load_missing_file_starts_at_zero(tmp_path: Path) -> None:
    quota = DailyQuota.load(tmp_path / "usage.json")
    assert quota.count == 0
    assert quota.usage_date == date.today().isoformat()


def test_record_and_save(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    quota = DailyQuota.load(path)
    assert quota.record() == 1
    quota.save(path)

    reloaded = DailyQuota.load(path)
    assert reloaded.count == 1


def test_from_dict_stale_date_resets_count() -> None:
    quota = DailyQuota.from_dict({"date": "2000-01-01", "count": 5})
    assert quota.count == 0
    assert quota.usage_date == date.today().isoformat()


def test_to_dict_round_trip() -> None:
    quota = DailyQuota(usage_date=date.today().isoformat(), count=4)
    assert quota.to_dict() == {"date": quota.usage_date, "count": 4}


def test_stale_date_resets_count(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    path.write_text(json.dumps({"date": "2000-01-01", "count": 5}), encoding="utf-8")

    quota = DailyQuota.load(path)
    assert quota.count == 0
    assert quota.usage_date == date.today().isoformat()


def test_remaining(tmp_path: Path) -> None:
    quota = DailyQuota(usage_date=date.today().isoformat(), count=3)
    assert quota.remaining(7) == 4
    assert quota.remaining(3) == 0
