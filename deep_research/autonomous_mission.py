"""Structured research mission schema, validation, and prompt building."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deep_research.tools.paths import slugify

VALID_DELIVERABLES = frozenset({"answer", "report", "mindmap", "slides", "papers", "paper_summary"})
VALID_DEPTHS = frozenset({"overview", "deep"})
CLARIFICATION_MESSAGE = (
    "What deliverables do you want for this research mission?\n\n"
    "Choose one or more:\n"
    "  - answer  — text synthesis in the chat response\n"
    "  - report  — formal Markdown + DOCX in the session Reports/ folder\n"
    "  - mindmap — mind map PNG in the session Diagrams/ folder\n"
    "  - slides  — PowerPoint deck in the session Slides/ folder\n"
    "  - papers  — download PDFs found during search to the session Papers/ folder\n"
    "  - paper_summary — structured summaries of downloaded PDFs in Papers/summaries/\n\n"
    "Re-run with deliverables specified in your mission JSON or example."
)

_DELIVERABLE_ALIASES = {
    "text": "answer",
    "summary": "answer",
    "docx": "report",
    "diagram": "mindmap",
    "mind_map": "mindmap",
    "pptx": "slides",
    "deck": "slides",
    "pdf": "papers",
    "pdfs": "papers",
    "paper_summaries": "paper_summary",
}


@dataclass(slots=True)
class ResearchMission:
    """Step-1 input for the autonomous research agent."""

    topic: str
    field: str
    objectives: list[str]
    deliverables: list[str]
    audience: str = "informed lay reader"
    depth: str = "deep"
    scope: str | None = None
    constraints: str | None = None
    success_criteria: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return slugify(self.topic)

    def normalized_deliverables(self) -> list[str]:
        normalized: list[str] = []
        for item in self.deliverables:
            token = str(item).strip().lower().replace(" ", "_")
            token = _DELIVERABLE_ALIASES.get(token, token)
            if token in VALID_DELIVERABLES and token not in normalized:
                normalized.append(token)
        return normalized

    def wants_artifact(self, name: str) -> bool:
        return name in self.normalized_deliverables()

    def recommended_source_mode(self) -> str:
        field_lower = self.field.lower()
        academic_hints = (
            "health",
            "nutrition",
            "medicine",
            "biology",
            "science",
            "materials",
            "physics",
            "chemistry",
            "engineering",
        )
        news_hints = ("policy", "news", "market", "business", "economics")
        if any(hint in field_lower for hint in news_hints):
            return "news"
        if any(hint in field_lower for hint in academic_hints):
            return "academic"
        return "general"

    def is_health_topic(self) -> bool:
        combined = f"{self.topic} {self.field}".lower()
        return any(
            term in combined
            for term in ("health", "nutrition", "medical", "medicine", "clinical", "diet")
        )


@dataclass(slots=True)
class MissionValidation:
    """Outcome of pre-flight mission validation."""

    ok: bool
    mission: ResearchMission | None = None
    clarification_message: str | None = None
    errors: list[str] = field(default_factory=list)


def normalize_deliverables(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    mission = ResearchMission(
        topic="x",
        field="x",
        objectives=["x"],
        deliverables=list(raw),
    )
    return mission.normalized_deliverables()


def mission_from_dict(data: dict[str, Any]) -> ResearchMission:
    topic = str(data.get("topic") or "").strip()
    if not topic:
        raise ValueError("mission topic is required")

    field = str(data.get("field") or "general").strip()
    objectives_raw = data.get("objectives") or []
    if not isinstance(objectives_raw, list) or not objectives_raw:
        raise ValueError("mission objectives must be a non-empty list")

    objectives = [str(item).strip() for item in objectives_raw if str(item).strip()]
    if not objectives:
        raise ValueError("mission objectives must contain at least one item")

    deliverables_raw = data.get("deliverables")
    deliverables = (
        [str(item) for item in deliverables_raw]
        if isinstance(deliverables_raw, list)
        else []
    )

    depth = str(data.get("depth") or "deep").strip().lower()
    if depth not in VALID_DEPTHS:
        depth = "deep"

    criteria_raw = data.get("success_criteria") or []
    success_criteria = (
        [str(item).strip() for item in criteria_raw if str(item).strip()]
        if isinstance(criteria_raw, list)
        else []
    )

    return ResearchMission(
        topic=topic,
        field=field,
        objectives=objectives,
        deliverables=deliverables,
        audience=str(data.get("audience") or "informed lay reader").strip(),
        depth=depth,
        scope=str(data.get("scope")).strip() if data.get("scope") else None,
        constraints=str(data.get("constraints")).strip() if data.get("constraints") else None,
        success_criteria=success_criteria,
    )


def mission_from_json(path: str | Path) -> ResearchMission:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("mission file must contain a JSON object")
    return mission_from_dict(payload)


def validate_mission(mission: ResearchMission) -> MissionValidation:
    errors: list[str] = []

    if not mission.topic.strip():
        errors.append("topic is required")
    if not mission.objectives:
        errors.append("objectives must be non-empty")
    if mission.depth not in VALID_DEPTHS:
        errors.append("depth must be overview or deep")

    deliverables = mission.normalized_deliverables()
    if not deliverables:
        return MissionValidation(
            ok=False,
            mission=mission,
            clarification_message=CLARIFICATION_MESSAGE,
        )

    if errors:
        return MissionValidation(ok=False, mission=mission, errors=errors)

    normalized = ResearchMission(
        topic=mission.topic,
        field=mission.field,
        objectives=mission.objectives,
        deliverables=deliverables,
        audience=mission.audience,
        depth=mission.depth,
        scope=mission.scope,
        constraints=mission.constraints,
        success_criteria=mission.success_criteria,
    )
    return MissionValidation(ok=True, mission=normalized)


def _format_list(items: list[str], *, bullet: str = "-") -> str:
    return "\n".join(f"{bullet} {item}" for item in items)


def _deliverable_checklist(mission: ResearchMission) -> str:
    lines: list[str] = []
    session = _active_session_for_mission()

    lines.append("- Produce a thorough text answer in your final response")

    if mission.wants_artifact("report"):
        lines.append("- create_research_report → session Reports/")
    if mission.wants_artifact("mindmap"):
        lines.append("- create_diagram (diagram_type=mindmap) → session Diagrams/")
    if mission.wants_artifact("slides"):
        lines.append("- create_slide_deck → session Slides/ (embed mind map PNG if available)")
    if mission.wants_artifact("papers"):
        lines.append("- download_research_pdfs for direct PDF URLs → session Papers/")
    if mission.wants_artifact("paper_summary"):
        lines.append("- summarize_downloaded_papers after PDFs → Papers/summaries/")

    lines.append("- complete_mission with summary, artifacts list, and assumptions")

    if not any(mission.wants_artifact(d) for d in ("report", "mindmap", "slides", "papers")):
        lines.append("- Do NOT create report, diagram, slide, or PDF files (answer only)")

    if session:
        lines.append(f"- All artifacts must be saved under: {session.relative_root()}")

    return _format_list(lines)


def _active_session_for_mission():
    from deep_research.session_context import get_active_session

    return get_active_session()


def _allowed_tools(mission: ResearchMission) -> str:
    tools = ["search_research_literature", "verify_sources", "complete_mission"]
    if mission.wants_artifact("papers"):
        tools.insert(1, "download_research_pdfs")
    if mission.wants_artifact("paper_summary"):
        tools.append("summarize_downloaded_papers")
    tools.append("query_session_corpus")
    if mission.wants_artifact("report"):
        tools.append("create_research_report")
    if mission.wants_artifact("mindmap"):
        tools.append("create_diagram")
    if mission.wants_artifact("slides"):
        tools.append("create_slide_deck")
    return _format_list(tools)


def build_mission_prompt(
    mission: ResearchMission,
    *,
    prior_context: str | None = None,
    follow_up_prompt: str | None = None,
) -> str:
    """Build the single mission brief sent to the autonomous agent."""
    deliverables = mission.normalized_deliverables()
    session = _active_session_for_mission()
    sections = [
        "# Research mission",
        "",
        f"**Topic:** {mission.topic}",
        f"**Field:** {mission.field}",
        f"**Audience:** {mission.audience}",
        f"**Depth:** {mission.depth}",
        f"**Recommended search source_mode:** {mission.recommended_source_mode()}",
    ]
    if session:
        sections.append(f"**Session folder:** {session.relative_root()}")
    sections.extend(
        [
            "",
            "## Objectives",
            _format_list(mission.objectives),
            "",
            "## Deliverables (execute ONLY these)",
            _format_list(deliverables),
            "",
            "## Execution checklist",
            _deliverable_checklist(mission),
            "",
            "## Allowed tools",
            _allowed_tools(mission),
        ]
    )

    if prior_context:
        sections.extend(["", prior_context])

    if follow_up_prompt:
        sections.extend(
            [
                "",
                "## Follow-up request",
                follow_up_prompt,
                "",
                "Continue the research thread. Address only this follow-up while building on prior turns.",
            ]
        )

    if mission.scope:
        sections.extend(["", "## Scope", mission.scope])
    if mission.constraints:
        sections.extend(["", "## Constraints", mission.constraints])
    if mission.success_criteria:
        sections.extend(["", "## Success criteria", _format_list(mission.success_criteria)])

    sections.extend(
        [
            "",
            "## Rules",
            "- Do not ask the user any questions. Make reasonable assumptions and list them.",
            "- Run 2–4 targeted searches before synthesizing.",
            f"- Use search_research_literature with source_mode=\"{mission.recommended_source_mode()}\".",
            "- Call complete_mission when all deliverables are finished.",
        ]
    )

    if mission.is_health_topic():
        sections.append(
            "- Include an educational health disclaimer in the report/answer (not personal medical advice)."
        )

    return "\n".join(sections)


def verify_deliverables(
    mission: ResearchMission,
    *,
    answer: str | None = None,
) -> list[str]:
    """
    Return missing deliverable tokens after a run.

    Checks the active session folder for artifacts and optional text answer.
    """
    from deep_research.session_context import get_active_session, list_session_files

    deliverables = mission.normalized_deliverables()
    missing: list[str] = []
    session = get_active_session()

    if session is None:
        from deep_research.tools.paths import (
            DIAGRAMS_DIR,
            PAPERS_DIR,
            REPORTS_DIR,
            SLIDES_DIR,
        )

        slug = mission.slug

        def _has_file(directory: Path, *suffixes: str) -> bool:
            if not directory.exists():
                return False
            for path in directory.iterdir():
                if not path.is_file():
                    continue
                name = path.name.lower()
                if slug in name and name.endswith(suffixes):
                    return True
            return False

        if mission.wants_artifact("report"):
            if not _has_file(REPORTS_DIR, ".docx", ".md"):
                missing.append("report")
        if mission.wants_artifact("mindmap"):
            if not _has_file(DIAGRAMS_DIR, ".png", ".svg"):
                missing.append("mindmap")
        if mission.wants_artifact("slides"):
            if not _has_file(SLIDES_DIR, ".pptx"):
                missing.append("slides")
        if mission.wants_artifact("papers"):
            if not PAPERS_DIR.exists() or not any(PAPERS_DIR.iterdir()):
                missing.append("papers")
        if mission.wants_artifact("answer"):
            if not (answer or "").strip():
                missing.append("answer")
        return missing

    def _has_suffix(files: list[Path], *suffixes: str) -> bool:
        return any(f.name.lower().endswith(suffixes) for f in files)

    if mission.wants_artifact("report"):
        if not _has_suffix(list_session_files(session, "Reports"), ".docx", ".md"):
            missing.append("report")
    if mission.wants_artifact("mindmap"):
        if not _has_suffix(list_session_files(session, "Diagrams"), ".png", ".svg"):
            missing.append("mindmap")
    if mission.wants_artifact("slides"):
        if not _has_suffix(list_session_files(session, "Slides"), ".pptx"):
            missing.append("slides")
    if mission.wants_artifact("papers"):
        if not list_session_files(session, "Papers"):
            missing.append("papers")
    if mission.wants_artifact("paper_summary"):
        summaries_dir = session.root / "Papers" / "summaries"
        has_summary = summaries_dir.exists() and any(summaries_dir.glob("*.md"))
        if not has_summary:
            missing.append("paper_summary")

    if mission.wants_artifact("answer"):
        text = (answer or "").strip()
        if not text:
            missing.append("answer")

    return missing


def collect_artifacts(mission: ResearchMission) -> list[str]:
    """Collect project-relative artifact paths for this mission."""
    from deep_research.session_context import collect_session_artifacts, get_active_session

    session = get_active_session()
    if session:
        return collect_session_artifacts(session)

    from deep_research.tools.paths import (
        DIAGRAMS_DIR,
        PAPERS_DIR,
        PROJECT_ROOT,
        REPORTS_DIR,
        SLIDES_DIR,
    )

    slug = mission.slug
    artifacts: list[str] = []

    for directory in (REPORTS_DIR, DIAGRAMS_DIR, SLIDES_DIR, PAPERS_DIR):
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and slug in path.name.lower():
                artifacts.append(str(path.relative_to(PROJECT_ROOT)))

    return artifacts
