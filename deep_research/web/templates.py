"""Built-in mission templates for Streamlit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import json

from agent_core.io import load_json

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "missions" / "templates"

BUILTIN_TEMPLATES: dict[str, dict[str, Any]] = {
    "literature_review": {
        "topic": "",
        "field": "science",
        "objectives": [
            "Survey peer-reviewed literature on the topic",
            "Identify consensus, debate, and research gaps",
            "Synthesize key findings for an informed audience",
        ],
        "deliverables": ["answer", "report", "papers"],
        "depth": "deep",
        "audience": "research-informed reader",
        "success_criteria": [
            "At least 5 credible sources cited",
            "Clear distinction between established and emerging findings",
        ],
    },
    "competitive_landscape": {
        "topic": "",
        "field": "business",
        "objectives": [
            "Map major players and market positioning",
            "Summarize recent developments and trends",
            "Highlight opportunities and risks",
        ],
        "deliverables": ["answer", "report", "mindmap", "slides"],
        "depth": "overview",
        "audience": "business stakeholder",
    },
    "health_deep_dive": {
        "topic": "",
        "field": "health",
        "objectives": [
            "Explain mechanisms and evidence quality",
            "Cover practical implications for general readers",
            "Note limitations and areas of scientific debate",
        ],
        "deliverables": ["answer", "report", "mindmap", "papers"],
        "depth": "deep",
        "audience": "informed lay reader",
        "constraints": "Educational only — not personal medical advice",
    },
    "policy_brief": {
        "topic": "",
        "field": "policy",
        "objectives": [
            "Summarize current policy landscape and stakeholders",
            "Analyze recent news and official sources",
            "Provide balanced recommendations",
        ],
        "deliverables": ["answer", "report", "slides"],
        "depth": "overview",
        "audience": "policy analyst",
    },
}


def list_template_names() -> list[str]:
    names = list(BUILTIN_TEMPLATES.keys())
    if TEMPLATES_DIR.exists():
        for path in sorted(TEMPLATES_DIR.glob("*.json")):
            if path.stem not in names:
                names.append(path.stem)
    return names


def load_template(name: str) -> dict[str, Any] | None:
    if name in BUILTIN_TEMPLATES:
        return dict(BUILTIN_TEMPLATES[name])
    path = TEMPLATES_DIR / f"{name}.json"
    if path.exists():
        data = load_json(path, default=None)
        return data if isinstance(data, dict) else None
    return None


def save_user_template(name: str, mission: dict[str, Any]) -> Path:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    path = TEMPLATES_DIR / f"{name}.json"
    path.write_text(json.dumps(mission, indent=2), encoding="utf-8")
    return path
