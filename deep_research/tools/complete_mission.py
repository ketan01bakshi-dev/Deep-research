"""Record mission completion and artifact manifest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from agent_core.io import save_json
from cursor_sdk import CustomTool, CustomToolContext

from deep_research.session_context import get_active_session
from deep_research.tools.paths import (
    missions_directory,
    relative_to_project_path,
    slugify,
    unique_path,
)


def _completion_path() -> tuple[Any, str]:
    """Return (directory, filename) for completion log."""
    session = get_active_session()
    if session:
        return session.root, "completion.json"
    directory = missions_directory()
    return directory, f"{slugify('research-mission')}.json"


def complete_mission(
    args: dict[str, Any],
    _ctx: CustomToolContext,
) -> str:
    """Log mission completion with summary and artifact manifest."""
    summary = str(args.get("summary") or "").strip()
    if not summary:
        raise ValueError("summary is required")

    title = str(args.get("title") or "research-mission").strip()
    artifacts_raw = args.get("artifacts") or []
    assumptions_raw = args.get("assumptions") or []
    success_met = bool(args.get("success_criteria_met", True))

    if not isinstance(artifacts_raw, list):
        raise ValueError("artifacts must be a list of strings")
    if not isinstance(assumptions_raw, list):
        raise ValueError("assumptions must be a list of strings")

    artifacts = [str(item).strip() for item in artifacts_raw if str(item).strip()]
    assumptions = [str(item).strip() for item in assumptions_raw if str(item).strip()]

    directory, filename = _completion_path()
    session = get_active_session()
    if session:
        log_path = directory / filename
    else:
        base = slugify(title)
        log_path = unique_path(directory, f"{base}.json")

    payload = {
        "title": title,
        "summary": summary,
        "artifacts": artifacts,
        "assumptions": assumptions,
        "success_criteria_met": success_met,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json(log_path, payload)

    return json.dumps(
        {
            "status": "completed",
            "mission_log": relative_to_project_path(log_path),
            "artifact_count": len(artifacts),
            "message": "Mission marked complete. Stop execution.",
        },
        indent=2,
    )


COMPLETE_MISSION_TOOL = CustomTool(
    execute=complete_mission,
    description=(
        "Mark the research mission complete. Call last with summary, artifact paths, "
        "assumptions, and success_criteria_met. Saves completion.json in the session folder."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Mission topic title."},
            "summary": {"type": "string", "description": "Brief completion summary."},
            "artifacts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Project-relative paths to created files.",
            },
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Assumptions made due to ambiguity.",
            },
            "success_criteria_met": {
                "type": "boolean",
                "description": "Whether mission success criteria were satisfied.",
            },
        },
        "required": ["summary"],
    },
)
