"""Health-related research examples for demonstrating the stateless research agent (phase 1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResearchExample:
    """A single demo research question."""

    id: str
    title: str
    prompt: str


HEALTH_RESEARCH_EXAMPLES: tuple[ResearchExample, ...] = (
    ResearchExample(
        id="protein_digestion",
        title="How the body digests dietary protein",
        prompt=(
            "Research how the human body digests dietary protein from ingestion to "
            "absorption. Cover the roles of stomach acid, pepsin, pancreatic proteases, "
            "brush-border peptidases, and amino acid absorption in the small intestine. "
            "Explain what happens to different protein sources (e.g., whey vs. casein vs. "
            "legumes) in terms of digestion speed and completeness."
        ),
    ),
    ResearchExample(
        id="protein_requirements",
        title="Daily protein needs and activity",
        prompt=(
            "Research recommended daily protein intake for healthy adults. Explain how "
            "activity level, age, and goals (maintenance vs. muscle gain) change "
            "requirements. Summarize common guidelines from major health organizations."
        ),
    ),
    ResearchExample(
        id="protein_sources",
        title="Plant vs. animal protein quality",
        prompt=(
            "Research and compare plant-based and animal-based dietary protein sources. "
            "Cover protein completeness (essential amino acid profiles), digestibility "
            "(e.g., PDCAAS/DIAAS concepts), and practical implications for mixed diets."
        ),
    ),
    ResearchExample(
        id="protein_metabolism",
        title="Fate of excess dietary protein",
        prompt=(
            "Research what happens when dietary protein intake exceeds what the body needs "
            "for tissue repair and maintenance. Explain deamination, urea production, and "
            "whether excess protein is preferentially stored, oxidized, or converted to "
            "other substrates."
        ),
    ),
    ResearchExample(
        id="gut_microbiome_protein",
        title="Gut microbiome and protein fermentation",
        prompt=(
            "Research how undigested or partially digested protein reaches the colon and "
            "interacts with the gut microbiome. Summarize potential metabolites (e.g., "
            "branched-chain fatty acids, amines) and what is known vs. uncertain about "
            "health effects."
        ),
    ),
)


def get_example(example_id: str) -> ResearchExample:
    """Return a demo example by id."""
    for example in HEALTH_RESEARCH_EXAMPLES:
        if example.id == example_id:
            return example
    known = ", ".join(example.id for example in HEALTH_RESEARCH_EXAMPLES)
    raise KeyError(f"Unknown example {example_id!r}. Choose one of: {known}")
