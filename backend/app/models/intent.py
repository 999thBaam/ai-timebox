from __future__ import annotations
"""Intent Hypothesis Framework 2.0 - Core intent model."""
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4


class ActivityNature(str, Enum):
    """Type of activity for cognitive load estimation."""
    DEEP_WORK = "DEEP_WORK"
    SHALLOW_WORK = "SHALLOW_WORK"
    MEETING = "MEETING"
    BREAK = "BREAK"
    PERSONAL = "PERSONAL"
    ADMIN = "ADMIN"


class EnergyLevel(str, Enum):
    """Required energy level for an activity."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TemporalFlexibility(str, Enum):
    """How flexible is the timing."""
    FIXED = "FIXED"
    FLEXIBLE = "FLEXIBLE"
    ANYTIME = "ANYTIME"


class SpatialFlexibility(str, Enum):
    """How flexible is the location."""
    LOCATION_BOUND = "LOCATION_BOUND"
    FLEXIBLE = "FLEXIBLE"


class SocialRisk(str, Enum):
    """Risk of social embarrassment if AI makes wrong assumption."""
    NONE = "NONE"
    LOW = "LOW"
    HIGH = "HIGH"


class BlockingFactor(str, Enum):
    """How much this unknown blocks progress."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"


@dataclass
class TransitionProfile:
    """Cognitive transition requirements for an activity."""
    ramp_up_minutes: int = 0      # Time to reach full focus (0-60)
    cool_down_minutes: int = 0    # Time to context-switch afterward (0-30)
    context_residue: float = 0.0  # Lingering cognitive load (0.0-1.0)

    def __post_init__(self) -> None:
        assert 0 <= self.ramp_up_minutes <= 60
        assert 0 <= self.cool_down_minutes <= 30
        assert 0.0 <= self.context_residue <= 1.0


@dataclass
class Volatility:
    """How stable/predictable is this event."""
    stability_score: float = 0.8      # How likely to stay as planned (0.0-1.0)
    dependencies: list[str] = field(default_factory=list)  # External dependencies
    fallback_action: str | None = None  # What to do if event fails

    def __post_init__(self) -> None:
        assert 0.0 <= self.stability_score <= 1.0


@dataclass
class Unknown:
    """A parameter that couldn't be determined from user input."""
    parameter: str                # Which field is unknown
    blocking_factor: BlockingFactor
    resolution_deadline: datetime | None = None
    deferrable: bool = True


@dataclass
class IntentHypothesis:
    """
    Complete intent hypothesis (IHF 2.0).
    
    Represents the system's understanding of what the user wants to do,
    including what is known vs unknown, and confidence levels.
    """
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    raw_input: str = ""           # Original user text

    # Core intent
    goal: str = ""                # What user wants to accomplish
    participants: list[str] = field(default_factory=list)  # People involved
    activity_nature: ActivityNature = ActivityNature.SHALLOW_WORK

    # Cognitive requirements
    energy_level_required: EnergyLevel = EnergyLevel.MEDIUM
    transition_profile: TransitionProfile = field(default_factory=TransitionProfile)

    # Flexibility
    temporal_flexibility: TemporalFlexibility = TemporalFlexibility.FLEXIBLE
    preferred_window: tuple[time, time] | None = None
    duration_estimate_minutes: int = 30
    spatial_flexibility: SpatialFlexibility = SpatialFlexibility.FLEXIBLE

    # Risk
    social_risk: SocialRisk = SocialRisk.NONE
    volatility: Volatility = field(default_factory=Volatility)

    # Epistemic state
    unknowns: list[Unknown] = field(default_factory=list)
    confidence: float = 0.5       # Overall parse confidence (0.0-1.0)

    def __post_init__(self) -> None:
        assert 0.0 <= self.confidence <= 1.0

    def with_resolved_unknown(self, parameter: str, value: str) -> "IntentHypothesis":
        """Return a new hypothesis with an unknown resolved."""
        # Create a shallow copy and update
        from dataclasses import replace
        new_unknowns = [u for u in self.unknowns if u.parameter != parameter]
        # Apply the value based on parameter name
        updates: dict = {"unknowns": new_unknowns}
        if parameter == "duration":
            updates["duration_estimate_minutes"] = int(value.replace("h", "").replace("min", "")) * (60 if "h" in value else 1)
        # Add more parameter handlers as needed
        return replace(self, **updates)

    @property
    def has_critical_unknowns(self) -> bool:
        """Check if there are any critical unknowns that must be resolved."""
        return any(
            u.blocking_factor == BlockingFactor.CRITICAL and not u.deferrable
            for u in self.unknowns
        )
