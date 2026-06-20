"""Load .env from a project root."""

from __future__ import annotations

from pathlib import Path


def load_agent_env(
    project_root: Path | str,
    *,
    env_filename: str = ".env",
) -> bool:
    """
    Load environment variables from project_root/.env.

    Returns True if python-dotenv loaded a file, False otherwise.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    env_path = Path(project_root) / env_filename
    return bool(load_dotenv(env_path))
