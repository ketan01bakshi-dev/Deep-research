from __future__ import annotations

from datetime import date
from pathlib import Path

from agent_core.paths import AgentLayout


def test_from_root_resolves_paths(tmp_path: Path) -> None:
    layout = AgentLayout.from_root(tmp_path)
    assert layout.root == tmp_path.resolve()
    assert layout.config_dir == tmp_path / "config"
    assert layout.profile_dir == tmp_path / "profile"
    assert layout.results_dir == tmp_path / "results"
    assert layout.env_file == tmp_path / ".env"


def test_today_str_matches_iso_date() -> None:
    layout = AgentLayout.from_root(".")
    assert layout.today_str() == date.today().isoformat()


def test_results_dirs(tmp_path: Path) -> None:
    layout = AgentLayout.from_root(tmp_path)
    today = layout.today_str()
    assert layout.today_results_dir() == tmp_path / "results" / today
    assert layout.latest_results_dir() == tmp_path / "results" / "latest"
