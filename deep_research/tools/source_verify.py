"""Source verification and citation tools."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

from cursor_sdk import CustomTool, CustomToolContext

from deep_research.session_context import get_active_session
from deep_research.tools.paths import PROJECT_ROOT
from agent_core.io import load_json, save_json


def _head_check(url: str, *, timeout: float = 8.0) -> dict[str, Any]:
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": "DeepResearch/1.0"})
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            return {
                "url": url,
                "ok": 200 <= status < 400,
                "status": status,
                "content_type": content_type,
                "paywalled_hint": "login" in content_type.lower() or status in (401, 403),
            }
    except Exception as exc:
        return {"url": url, "ok": False, "status": None, "error": str(exc)}


def verify_sources(
    args: dict[str, Any],
    _ctx: CustomToolContext,
) -> str:
    """HEAD-check URLs and update sources.json with verification status."""
    urls_raw = args.get("urls") or []
    if not isinstance(urls_raw, list):
        raise ValueError("urls must be a list of strings")

    session = get_active_session()
    sources_path = session.root / "sources.json" if session else None
    existing: list[dict] = []
    if sources_path and sources_path.exists():
        data = load_json(sources_path, default={})
        existing = list(data.get("sources") or []) if isinstance(data, dict) else []

    url_set = {str(u).strip() for u in urls_raw if str(u).strip()}
    if not url_set and existing:
        url_set = {str(s.get("url") or "") for s in existing if s.get("url")}

    verified: list[dict] = []
    for url in sorted(url_set):
        if not url:
            continue
        check = _head_check(url)
        prior = next((s for s in existing if s.get("url") == url), {})
        verified.append({**prior, **check})

    if session and verified:
        save_json(sources_path, {"sources": verified, "count": len(verified)})

    dead = [v["url"] for v in verified if not v.get("ok")]
    payload = {
        "verified_count": sum(1 for v in verified if v.get("ok")),
        "dead_links": dead,
        "sources": verified,
        "sources_path": str(sources_path.relative_to(PROJECT_ROOT)) if sources_path else None,
    }
    return json.dumps(payload, indent=2)


VERIFY_SOURCES_TOOL = CustomTool(
    execute=verify_sources,
    description=(
        "Verify research source URLs with HTTP HEAD requests. Updates sources.json "
        "with ok/dead_link status. Pass urls list or rely on existing sources.json."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "URLs to verify (optional if sources.json exists).",
            },
        },
    },
)
