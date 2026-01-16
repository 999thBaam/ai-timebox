from __future__ import annotations
"""Timeline models - Scheduled blocks and candidates."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4


@dataclass
class ScheduledBlock:
    """A single scheduled event in the timeline."""
    id: UUID = field(default_factory=uuid4)
    intent_id: UUID = field(default_factory=uuid4)  # Link to IntentHypothesis
    user_id: UUID = field(default_factory=uuid4)

    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)

    goal: str = ""
    activity_nature: str = "SHALLOW_WORK"

    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0
    is_locked: bool = False  # User manually locked this

    @property
    def duration_minutes(self) -> int:
        """Total duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    @property
    def total_blocked_minutes(self) -> int:
        """Duration including buffers."""
        return self.buffer_before_minutes + self.duration_minutes + self.buffer_after_minutes


@dataclass
class StateCheckpoint:
    """
    Compressed state snapshot for storage efficiency.
    
    Full trajectories live in Redis during planning;
    only checkpoints are persisted to PostgreSQL.
    """
    timestamp: datetime
    checkpoint_type: Literal["START", "PEAK_LOAD", "END"]
    cognitive_load: float
    energy_level: float
    context_residue: float

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "checkpoint_type": self.checkpoint_type,
            "cognitive_load": self.cognitive_load,
            "energy_level": self.energy_level,
            "context_residue": self.context_residue,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StateCheckpoint":
        """Deserialize from JSON storage."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            checkpoint_type=data["checkpoint_type"],
            cognitive_load=data["cognitive_load"],
            energy_level=data["energy_level"],
            context_residue=data["context_residue"],
        )


@dataclass
class CandidateTimeline:
    """
    A potential schedule being evaluated by the planner.
    
    Multiple candidates are generated, simulated, and scored
    before the best one is selected.
    """
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    blocks: list[ScheduledBlock] = field(default_factory=list)

    # Quality scores (0.0-1.0)
    goal_fulfillment: float = 0.0     # How well goals are met
    state_safety_score: float = 0.0   # Min safety margin across timeline
    stability_score: float = 0.0      # Robustness to disruption
    overall_score: float = 0.0        # Weighted combination

    # Simulation results (compressed for DB)
    state_checkpoints: list[StateCheckpoint] = field(default_factory=list)
    violated_policies: list[UUID] = field(default_factory=list)

    def compute_overall_score(
        self,
        goal_weight: float = 0.4,
        safety_weight: float = 0.4,
        stability_weight: float = 0.2,
    ) -> float:
        """Compute weighted overall score."""
        self.overall_score = (
            self.goal_fulfillment * goal_weight +
            self.state_safety_score * safety_weight +
            self.stability_score * stability_weight
        )
        return self.overall_score
