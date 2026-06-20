"""Multi-turn conversational health research examples (phase 2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """One user message in a scripted conversation."""

    prompt: str


@dataclass(frozen=True, slots=True)
class ConversationExample:
    """A multi-turn research conversation that builds on prior context."""

    id: str
    title: str
    turns: tuple[ConversationTurn, ...]


CONVERSATION_EXAMPLES: tuple[ConversationExample, ...] = (
    ConversationExample(
        id="protein_digestion_deep_dive",
        title="Protein digestion: multi-turn deep dive",
        turns=(
            ConversationTurn(
                "Research how the human body digests dietary protein from ingestion "
                "through absorption. Cover stomach acid, pepsin, pancreatic proteases, "
                "and small-intestinal absorption."
            ),
            ConversationTurn(
                "Based on what you just explained, which step is usually the "
                "rate-limiting bottleneck for a typical mixed meal?"
            ),
            ConversationTurn(
                "Compare whey and casein using your earlier breakdown — focus on "
                "digestion speed, amino acid release patterns, and practical timing "
                "for post-workout vs. overnight recovery."
            ),
            ConversationTurn(
                "Summarize our entire conversation as a structured research brief "
                "with sections, key takeaways, and source links where available."
            ),
        ),
    ),
    ConversationExample(
        id="protein_requirements_coaching",
        title="Protein needs: from guidelines to personal plan",
        turns=(
            ConversationTurn(
                "Research recommended daily protein intake for healthy adults. "
                "Include how activity level and age affect requirements."
            ),
            ConversationTurn(
                "For a 70 kg adult who strength-trains 4 days per week, estimate a "
                "reasonable daily protein range using the guidelines you cited."
            ),
            ConversationTurn(
                "They prefer mostly plant-based meals. Based on our discussion, "
                "what are two practical strategies to hit that protein target without "
                "relying on supplements?"
            ),
        ),
    ),
    ConversationExample(
        id="leucine_muscle_synthesis",
        title="Leucine threshold and meal comparisons",
        turns=(
            ConversationTurn(
                "Research the role of leucine in muscle protein synthesis after "
                "resistance training. Note any commonly cited per-meal leucine "
                "thresholds in the literature."
            ),
            ConversationTurn(
                "Using the leucine threshold you described, compare a 30 g whey "
                "shake versus 30 g of cooked lentils as post-workout options."
            ),
            ConversationTurn(
                "If the lentil option falls short on leucine, suggest minimal "
                "adjustments that stay plant-based — build on your prior comparison."
            ),
        ),
    ),
    ConversationExample(
        id="gut_health_protein_followup",
        title="Protein digestion and gut health thread",
        turns=(
            ConversationTurn(
                "Research how undigested or partially digested protein reaches the "
                "colon and interacts with the gut microbiome."
            ),
            ConversationTurn(
                "Which factors from our protein digestion discussion — meal size, "
                "protein type, or digestive enzymes — most influence how much protein "
                "reaches the colon?"
            ),
            ConversationTurn(
                "Give a balanced, evidence-aware summary of what is known vs. "
                "speculative about health implications, referencing what we've covered."
            ),
        ),
    ),
)


def get_conversation_example(example_id: str) -> ConversationExample:
    """Return a conversational demo by id."""
    for example in CONVERSATION_EXAMPLES:
        if example.id == example_id:
            return example
    known = ", ".join(example.id for example in CONVERSATION_EXAMPLES)
    raise KeyError(f"Unknown conversation example {example_id!r}. Choose one of: {known}")
