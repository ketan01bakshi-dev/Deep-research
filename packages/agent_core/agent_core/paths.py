"""Project directory layout for agent pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class AgentLayout:
    root: Path
    config_dir: Path
    profile_dir: Path
    results_dir: Path
    env_file: Path

    @classmethod
    def from_root(
        cls,
        root: Path | str,
        *,
        config_dir: str = "config",
        profile_dir: str = "profile",
        results_dir: str = "results",
        env_file: str = ".env",
    ) -> AgentLayout:
        root_path = Path(root).resolve()
        return cls(
            root=root_path,
            config_dir=root_path / config_dir,
            profile_dir=root_path / profile_dir,
            results_dir=root_path / results_dir,
            env_file=root_path / env_file,
        )

    def today_str(self) -> str:
        return date.today().isoformat()

    def today_results_dir(self) -> Path:
        return self.results_dir / self.today_str()

    def latest_results_dir(self) -> Path:
        return self.results_dir / "latest"
