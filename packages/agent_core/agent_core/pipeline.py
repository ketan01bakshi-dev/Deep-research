"""Pipeline result envelope (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineResult:
    raw_count: int = 0
    matched_count: int = 0
    above_threshold: int = 0
    errors: list[str] = field(default_factory=list)
    artifacts: dict[str, Path] = field(default_factory=dict)
