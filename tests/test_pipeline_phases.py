"""Unit tests for multi-agent pipeline helpers."""

from __future__ import annotations

from deep_research.autonomous_mission import ResearchMission
from deep_research.pipeline import _phase_prompt


def _mission() -> ResearchMission:
    return ResearchMission(
        topic="Neural interfaces",
        field="neuroscience",
        objectives=["Survey recent work"],
        deliverables=["answer", "report"],
        scope="2020-2025",
    )


def test_phase_prompt_includes_phase_name():
    mission = _mission()
    for phase in ("search", "synthesize", "artifacts", "review"):
        prompt = _phase_prompt(mission, phase)
        assert "## Phase:" in prompt


def test_phase_prompt_includes_prior_context():
    mission = _mission()
    prompt = _phase_prompt(mission, "synthesize", prior="Earlier findings about BCI.")
    assert "Earlier findings about BCI." in prompt
