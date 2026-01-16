from __future__ import annotations
"""SQLAlchemy ORM models for database tables."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class UserORM(Base):
    """User account."""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)


class IntentHypothesisORM(Base):
    """Stored intent hypotheses."""
    __tablename__ = "intent_hypotheses"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class HumanStateORM(Base):
    """User's cognitive state (one per user)."""
    __tablename__ = "human_states"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)

    cognitive_load: Mapped[float] = mapped_column(Float, default=0.3)
    emotional_load: Mapped[float] = mapped_column(Float, default=0.2)
    energy_level: Mapped[float] = mapped_column(Float, default=0.7)
    context_residue: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    fragility: Mapped[float] = mapped_column(Float, default=0.3)
    chaos_tolerance: Mapped[float] = mapped_column(Float, default=0.5)


class SafetyPolicyORM(Base):
    """Safety policies with decay."""
    __tablename__ = "safety_policies"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    protected_dimension: Mapped[str] = mapped_column(Text, nullable=False)
    activation_condition: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    action: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    initial_strength: Mapped[float] = mapped_column(Float, nullable=False)
    current_strength: Mapped[float] = mapped_column(Float, nullable=False)
    decay_curve: Mapped[str] = mapped_column(Text, nullable=False)
    decay_rate: Mapped[float] = mapped_column(Float, nullable=False)
    ttl_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    override_signals: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    override_count: Mapped[int] = mapped_column(Integer, default=0)


class ScheduledBlockORM(Base):
    """Scheduled blocks in user's timeline."""
    __tablename__ = "scheduled_blocks"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    intent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intent_hypotheses.id"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    activity_nature: Mapped[str] = mapped_column(Text, nullable=False)
    buffer_before_minutes: Mapped[int] = mapped_column(Integer, default=0)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)


class TimelineChangeORM(Base):
    """Undo history - all changes to timeline."""
    __tablename__ = "timeline_changes"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    change_type: Mapped[str] = mapped_column(Text, nullable=False)  # ADD | MOVE | DELETE | MODIFY
    affected_blocks: Mapped[List[UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    before_state: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    after_state: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)  # USER | PLANNER | POLICY
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    undone: Mapped[bool] = mapped_column(Boolean, default=False)
    undone_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
