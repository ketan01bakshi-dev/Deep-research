"""Daily API quota tracking with automatic day rollover."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from agent_core.io import load_json, save_json


@dataclass
class DailyQuota:
    usage_date: str
    count: int

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        *,
        date_key: str = "date",
        count_key: str = "count",
    ) -> DailyQuota:
        today = date.today().isoformat()
        if not data or data.get(date_key) != today:
            return cls(usage_date=today, count=0)
        return cls(usage_date=today, count=int(data.get(count_key, 0)))

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        date_key: str = "date",
        count_key: str = "count",
    ) -> DailyQuota:
        return cls.from_dict(load_json(path, default=None), date_key=date_key, count_key=count_key)

    def remaining(self, limit: int) -> int:
        return max(0, limit - self.count)

    def record(self) -> int:
        self.count += 1
        return self.count

    def to_dict(
        self,
        *,
        date_key: str = "date",
        count_key: str = "count",
    ) -> dict[str, Any]:
        return {date_key: self.usage_date, count_key: self.count}

    def save(
        self,
        path: Path,
        *,
        date_key: str = "date",
        count_key: str = "count",
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        save_json(path, self.to_dict(date_key=date_key, count_key=count_key))

    def reset_if_new_day(self, today: str | None = None) -> None:
        today = today or date.today().isoformat()
        if self.usage_date != today:
            self.usage_date = today
            self.count = 0
