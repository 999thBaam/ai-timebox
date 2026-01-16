from __future__ import annotations
"""Human State Model - Cognitive state vector."""
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID


# Recovery rates (per hour)
COGNITIVE_RECOVERY_RATE = 0.1   # 10% per hour
RESIDUE_DECAY_RATE = 0.15       # 15% per hour
ENERGY_RECOVERY_RATE = 0.05     # 5% per hour (slow)

# Minimum values
MIN_COGNITIVE_LOAD = 0.1        # Never fully "empty"


@dataclass
class HumanState:
    """
    User's cognitive state vector.
    
    This is the heart of AI Timebox's human awareness.
    All values are 0.0-1.0 unless otherwise noted.
    """
    user_id: UUID
    updated_at: datetime

    # Core dimensions
    cognitive_load: float = 0.3       # Current mental utilization
    emotional_load: float = 0.2       # Stress / emotional weight
    energy_level: float = 0.7         # Available energy
    context_residue: float = 0.0      # Lingering context from last task

    # Meta-state
    confidence: float = 0.5           # Self-efficacy right now
    fragility: float = 0.3            # Likelihood of overwhelm
    chaos_tolerance: float = 0.5      # Ability to absorb disruption

    def __post_init__(self) -> None:
        """Validate all values are in range."""
        for attr in ["cognitive_load", "emotional_load", "energy_level",
                     "context_residue", "confidence", "fragility", "chaos_tolerance"]:
            value = getattr(self, attr)
            assert 0.0 <= value <= 1.0, f"{attr} must be 0.0-1.0, got {value}"

    @property
    def safe_load_capacity(self) -> float:
        """How much additional cognitive load can be safely added."""
        base = 1.0 - self.cognitive_load
        fragility_penalty = self.fragility * 0.3
        return max(0.0, base - fragility_penalty)

    def with_decay(self, now: datetime) -> "HumanState":
        """
        Compute state with natural recovery/decay.
        
        Idempotent: uses wall-clock delta, safe to call at any frequency.
        """
        minutes_elapsed = (now - self.updated_at).total_seconds() / 60
        hours = minutes_elapsed / 60

        return replace(
            self,
            updated_at=now,
            cognitive_load=max(
                MIN_COGNITIVE_LOAD,
                self.cognitive_load - COGNITIVE_RECOVERY_RATE * hours
            ),
            # emotional_load doesn't auto-decay (requires explicit intervention)
            energy_level=min(
                1.0,
                self.energy_level + ENERGY_RECOVERY_RATE * hours
            ),
            context_residue=max(
                0.0,
                self.context_residue - RESIDUE_DECAY_RATE * hours
            ),
        )

    def with_task_impact(
        self,
        cognitive_cost: float,
        energy_cost: float,
        residue: float,
    ) -> "HumanState":
        """
        Apply the impact of completing a task.
        
        Args:
            cognitive_cost: Immediate load added (0.0-1.0)
            energy_cost: Energy consumed (0.0-1.0)
            residue: Context residue left behind (0.0-1.0)
        """
        return replace(
            self,
            updated_at=datetime.now(),
            cognitive_load=min(1.0, self.cognitive_load + cognitive_cost),
            energy_level=max(0.0, self.energy_level - energy_cost),
            context_residue=min(1.0, residue),  # Replaces, doesn't add
        )

    def to_simplified_view(self) -> dict[str, str]:
        """
        Convert to user-facing simplified view.
        
        Users don't see raw values; they see actionable guidance.
        """
        # Energy level
        if self.energy_level > 0.7:
            energy = "high"
        elif self.energy_level > 0.4:
            energy = "medium"
        else:
            energy = "low"

        # Load status
        if self.cognitive_load > 0.7:
            load = "heavy"
        elif self.cognitive_load > 0.4:
            load = "moderate"
        else:
            load = "light"

        # Recommendation
        if self.energy_level < 0.3 or self.cognitive_load > 0.8:
            recommendation = "Consider taking a break soon"
        elif self.safe_load_capacity > 0.5:
            recommendation = "Good capacity for focused work"
        else:
            recommendation = "Light tasks recommended"

        return {
            "energy_level": energy,
            "load_status": load,
            "recommendation": recommendation,
        }
