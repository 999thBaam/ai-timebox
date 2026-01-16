from __future__ import annotations
"""Planner output models."""
from dataclasses import dataclass, field
from uuid import UUID

from app.models.timeline import CandidateTimeline


@dataclass
class PlannerExplanation:
    """
    Structured explanation facts.
    
    LLM only verbalizes these; the planner generates the facts.
    This preserves truthfulness and prevents post-hoc rationalization.
    """
    reasons: list[str] = field(default_factory=list)
    # Examples: ["energy_peak", "avoids_back_to_back_deep_work"]

    avoided: list[str] = field(default_factory=list)
    # Examples: ["late_night_placement", "no_buffer_after_meeting"]

    tradeoffs: list[str] = field(default_factory=list)
    # Examples: ["slightly_later_than_preferred"]

    confidence: float = 0.5

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "reasons": self.reasons,
            "avoided": self.avoided,
            "tradeoffs": self.tradeoffs,
            "confidence": self.confidence,
        }

    def to_verbalization_prompt(self) -> str:
        """Generate prompt for LLM verbalization."""
        parts = []

        if self.reasons:
            reasons_str = ", ".join(self.reasons)
            parts.append(f"Main reasons: {reasons_str}")

        if self.avoided:
            avoided_str = ", ".join(self.avoided)
            parts.append(f"Avoided: {avoided_str}")

        if self.tradeoffs:
            tradeoffs_str = ", ".join(self.tradeoffs)
            parts.append(f"Tradeoffs made: {tradeoffs_str}")

        return "; ".join(parts)


@dataclass
class PlannerResult:
    """
    Complete output from the planning process.
    
    Contains all candidates, the selected one, and explanations.
    """
    candidates: list[CandidateTimeline] = field(default_factory=list)
    selected: CandidateTimeline | None = None
    rejection_reasons: dict[UUID, str] = field(default_factory=dict)

    explanation_facts: PlannerExplanation = field(default_factory=PlannerExplanation)
    explanation_text: str | None = None  # LLM-verbalized

    @property
    def success(self) -> bool:
        """Whether planning succeeded."""
        return self.selected is not None

    @property
    def best_score(self) -> float:
        """Score of the selected timeline, or 0 if none."""
        return self.selected.overall_score if self.selected else 0.0
