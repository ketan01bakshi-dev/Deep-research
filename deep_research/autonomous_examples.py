"""Rich step-1 mission examples for the autonomous research agent."""

from __future__ import annotations

from dataclasses import dataclass

from deep_research.autonomous_mission import ResearchMission


@dataclass(frozen=True, slots=True)
class AutonomousMissionExample:
    id: str
    title: str
    mission: ResearchMission


AUTONOMOUS_MISSION_EXAMPLES: tuple[AutonomousMissionExample, ...] = (
    AutonomousMissionExample(
        id="protein_digestion_full",
        title="Protein digestion — full deliverable package",
        mission=ResearchMission(
            topic="How the human body digests dietary protein",
            field="nutrition / physiology",
            objectives=[
                "Explain the path from ingestion to amino acid absorption",
                "Cover stomach, pancreatic, and brush-border enzyme roles",
                "Compare whey, casein, and plant protein digestion speed",
            ],
            deliverables=["answer", "report", "mindmap", "slides", "papers"],
            audience="informed lay reader",
            depth="deep",
            scope="Human adults; focus on established physiology",
            constraints="Prefer peer-reviewed and government sources",
            success_criteria=[
                "At least 5 credible sources cited",
                "Report saved to Docs/Reports/",
                "Mind map PNG saved to Docs/Diagrams/",
                "Slide deck saved to Docs/Slides/",
            ],
        ),
    ),
    AutonomousMissionExample(
        id="solid_state_batteries",
        title="Solid-state batteries vs lithium-ion",
        mission=ResearchMission(
            topic="How solid-state batteries could replace lithium-ion in EVs",
            field="materials science / energy",
            objectives=[
                "Explain solid-state electrolyte approaches and maturity",
                "Compare energy density, safety, and manufacturing vs Li-ion",
                "Identify leading labs, companies, and commercialization timeline",
            ],
            deliverables=["answer", "report", "mindmap"],
            audience="informed lay reader with engineering interest",
            depth="deep",
            scope="2023–2026 developments; global perspective",
            constraints="Prefer peer-reviewed papers and industry whitepapers",
            success_criteria=[
                "Key tradeoffs and open problems clearly stated",
                "Report and mind map artifacts created",
            ],
        ),
    ),
    AutonomousMissionExample(
        id="agent_architecture_survey",
        title="Autonomous AI agent architectures survey",
        mission=ResearchMission(
            topic="Current approaches to building autonomous AI research agents",
            field="computer science / AI systems",
            objectives=[
                "Survey agent loop patterns (tool use, planning, memory)",
                "Compare SDK-based vs framework-based approaches",
                "Identify tradeoffs in reliability, cost, and observability",
            ],
            deliverables=["answer", "report", "slides"],
            audience="technical team evaluating agent stacks",
            depth="deep",
            scope="2024–2026; focus on production-oriented designs",
            constraints="Include official docs and credible engineering sources",
            success_criteria=[
                "Architecture comparison with pros/cons",
                "Slide deck suitable for a 10-minute briefing",
            ],
        ),
    ),
    AutonomousMissionExample(
        id="topic_only",
        title="Incomplete mission — triggers deliverables clarification",
        mission=ResearchMission(
            topic="Quantum computing applications in drug discovery",
            field="quantum computing / pharma",
            objectives=[
                "Summarize current use cases and limitations",
                "Identify companies and research groups leading the field",
            ],
            deliverables=[],
            audience="informed lay reader",
            depth="overview",
        ),
    ),
)


def get_autonomous_example(example_id: str) -> AutonomousMissionExample:
    for example in AUTONOMOUS_MISSION_EXAMPLES:
        if example.id == example_id:
            return example
    valid = ", ".join(example.id for example in AUTONOMOUS_MISSION_EXAMPLES)
    raise KeyError(f"Unknown autonomous example {example_id!r}. Valid: {valid}")
