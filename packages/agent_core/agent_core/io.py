"""YAML/JSON config and artifact I/O."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import yaml

try:
    import portalocker
except ImportError:  # pragma: no cover - optional on some platforms
    portalocker = None  # type: ignore[assignment]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@contextmanager
def file_lock(path: Path, *, exclusive: bool = True) -> Iterator[None]:
    """Acquire a lightweight file lock when portalocker is available."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    if portalocker is None:
        yield
        return
    mode = "wb" if exclusive else "rb"
    with lock_path.open(mode) as handle:
        flags = portalocker.LOCK_EX if exclusive else portalocker.LOCK_SH
        portalocker.lock(handle, flags)
        try:
            yield
        finally:
            portalocker.unlock(handle)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with file_lock(path, exclusive=True):
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, path)


def save_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False))


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
