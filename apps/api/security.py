"""API authentication and rate limiting."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)
_rate_lock = Lock()
_rate_buckets: dict[str, list[float]] = defaultdict(list)

MAX_TOPIC_LENGTH = 2000
MAX_PROMPT_LENGTH = 8000
MAX_OBJECTIVES = 20
DEFAULT_RATE_LIMIT = 30
DEFAULT_RATE_WINDOW_SECONDS = 60


def api_key_configured() -> str | None:
    return os.environ.get("DEEP_RESEARCH_API_KEY", "").strip() or None


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    expected = api_key_configured()
    if not expected:
        return
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def _client_key(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    limit: int = DEFAULT_RATE_LIMIT,
    window_seconds: int = DEFAULT_RATE_WINDOW_SECONDS,
) -> None:
    key = f"{_client_key(request)}:{request.url.path}"
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets[key]
        bucket[:] = [stamp for stamp in bucket if now - stamp < window_seconds]
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        bucket.append(now)


def validate_topic(topic: str) -> str:
    cleaned = topic.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="topic is required")
    if len(cleaned) > MAX_TOPIC_LENGTH:
        raise HTTPException(status_code=422, detail=f"topic exceeds {MAX_TOPIC_LENGTH} characters")
    return cleaned


def validate_prompt(prompt: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="prompt is required")
    if len(cleaned) > MAX_PROMPT_LENGTH:
        raise HTTPException(status_code=422, detail=f"prompt exceeds {MAX_PROMPT_LENGTH} characters")
    return cleaned
