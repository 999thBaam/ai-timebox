from __future__ import annotations
"""Safety Policy Model - Protective constraints with decay."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from app.models.human_state import HumanState


class DecayCurve(str, Enum):
    """How policy strength decays over time."""
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"
    STEP = "STEP"


class PolicySource(str, Enum):
    """Where this policy came from."""
    QUESTIONNAIRE = "QUESTIONNAIRE"  # Initial onboarding
    BEHAVIORAL = "BEHAVIORAL"        # Learned from behavior
    MANUAL = "MANUAL"                # User explicitly set


@dataclass
class ActivationCondition:
    """
    DSL-based activation condition.
    
    Safer than Python expressions - auditable and migration-friendly.
    """
    metric: Literal[
        "cognitive_load", "emotional_load", "energy_level",
        "context_residue", "confidence", "fragility", "chaos_tolerance"
    ]
    operator: Literal[">", ">=", "<", "<=", "=="]
    threshold: float

    def __post_init__(self) -> None:
        assert 0.0 <= self.threshold <= 1.0

    def evaluate(self, state: HumanState) -> bool:
        """Safely evaluate this condition against a HumanState."""
        value = getattr(state, self.metric)
        ops = {
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: abs(a - b) < 0.001,
        }
        return ops[self.operator](value, self.threshold)

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "metric": self.metric,
            "operator": self.operator,
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActivationCondition":
        """Deserialize from JSON storage."""
        return cls(
            metric=data["metric"],
            operator=data["operator"],
            threshold=data["threshold"],
        )


@dataclass
class SafetyPolicy:
    """
    A protective constraint that guards human state.
    
    Policies have decay (they weaken over time) and can be
    overridden by behavioral evidence contradicting them.
    """
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    name: str = ""
    source: PolicySource = PolicySource.QUESTIONNAIRE

    # What it protects
    protected_dimension: Literal[
        "confidence", "cognitive_load", "fragility", "chaos_tolerance"
    ] = "cognitive_load"

    # Activation
    activation_condition: ActivationCondition = field(
        default_factory=lambda: ActivationCondition(
            metric="cognitive_load",
            operator=">",
            threshold=0.7
        )
    )

    # Behavior when active
    action: dict = field(default_factory=dict)
    # Examples:
    #   {"type": "LIMIT_VISIBLE_TASKS", "max": 1}
    #   {"type": "INSERT_BUFFER", "minutes": 15}
    #   {"type": "BLOCK_COMPRESSION"}

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    initial_strength: float = 1.0
    current_strength: float = 1.0
    decay_curve: DecayCurve = DecayCurve.EXPONENTIAL
    decay_rate: float = 0.02  # Per day
    ttl_days: int | None = None

    # Override
    override_signals: list[str] = field(default_factory=list)
    override_count: int = 0

    def compute_effective_strength(self, now: datetime) -> float:
        """
        Compute current strength accounting for decay and overrides.
        
        Returns 0.0-1.0 strength value.
        """
        age_days = (now - self.created_at).days

        # Hard TTL check
        if self.ttl_days and age_days > self.ttl_days:
            return 0.0

        # Decay based on curve
        if self.decay_curve == DecayCurve.LINEAR:
            decay = self.decay_rate * age_days
        elif self.decay_curve == DecayCurve.EXPONENTIAL:
            decay = 1 - (1 - self.decay_rate) ** age_days
        else:  # STEP
            decay = 0.0 if age_days < self.decay_rate else 0.5

        # Override weakening
        override_penalty = self.override_count * 0.1

        return max(0.0, self.initial_strength - decay - override_penalty)

    def is_active(self, state: HumanState, now: datetime) -> bool:
        """Check if this policy is currently active."""
        strength = self.compute_effective_strength(now)
        if strength < 0.1:  # Too weak to matter
            return False
        return self.activation_condition.evaluate(state)

    def record_override(self) -> None:
        """Record that behavioral evidence contradicted this policy."""
        self.override_count += 1
