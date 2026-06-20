"""Hash-based cache invalidation for source files."""

from __future__ import annotations

import hashlib
from pathlib import Path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_unchanged(source: Path, cache_file: Path) -> bool:
    if not cache_file.exists():
        return False
    cached = cache_file.read_text(encoding="utf-8").strip()
    return cached == file_hash(source)


def write_cache_hash(cache_file: Path, source: Path) -> str:
    digest = file_hash(source)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(digest, encoding="utf-8")
    return digest
