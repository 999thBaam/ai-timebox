"""Initial migration - create all tables.

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-16

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=True),
    )

    # Human states table
    op.create_table(
        'human_states',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cognitive_load', sa.Float, default=0.3),
        sa.Column('emotional_load', sa.Float, default=0.2),
        sa.Column('energy_level', sa.Float, default=0.7),
        sa.Column('context_residue', sa.Float, default=0.0),
        sa.Column('confidence', sa.Float, default=0.5),
        sa.Column('fragility', sa.Float, default=0.3),
        sa.Column('chaos_tolerance', sa.Float, default=0.5),
    )

    # Intent hypotheses table
    op.create_table(
        'intent_hypotheses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('raw_input', sa.Text, nullable=False),
        sa.Column('hypothesis', postgresql.JSONB, nullable=False),
        sa.Column('resolved', sa.Boolean, default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_intent_hypotheses_user_id', 'intent_hypotheses', ['user_id'])

    # Safety policies table
    op.create_table(
        'safety_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('source', sa.Text, nullable=False),
        sa.Column('protected_dimension', sa.Text, nullable=False),
        sa.Column('activation_condition', postgresql.JSONB, nullable=False),
        sa.Column('action', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('initial_strength', sa.Float, nullable=False),
        sa.Column('current_strength', sa.Float, nullable=False),
        sa.Column('decay_curve', sa.Text, nullable=False),
        sa.Column('decay_rate', sa.Float, nullable=False),
        sa.Column('ttl_days', sa.Integer, nullable=True),
        sa.Column('override_signals', postgresql.ARRAY(sa.Text), default=[]),
        sa.Column('override_count', sa.Integer, default=0),
    )
    op.create_index('ix_safety_policies_user_id', 'safety_policies', ['user_id'])

    # Scheduled blocks table
    op.create_table(
        'scheduled_blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('intent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intent_hypotheses.id'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('goal', sa.Text, nullable=False),
        sa.Column('activity_nature', sa.Text, nullable=False),
        sa.Column('buffer_before_minutes', sa.Integer, default=0),
        sa.Column('buffer_after_minutes', sa.Integer, default=0),
        sa.Column('is_locked', sa.Boolean, default=False),
    )
    op.create_index('ix_scheduled_blocks_user_id', 'scheduled_blocks', ['user_id'])
    op.create_index('ix_scheduled_blocks_start_time', 'scheduled_blocks', ['start_time'])

    # Timeline changes table (for undo)
    op.create_table(
        'timeline_changes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('change_type', sa.Text, nullable=False),
        sa.Column('affected_blocks', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('before_state', postgresql.JSONB, nullable=False),
        sa.Column('after_state', postgresql.JSONB, nullable=False),
        sa.Column('trigger', sa.Text, nullable=False),
        sa.Column('explanation', sa.Text, nullable=False),
        sa.Column('undone', sa.Boolean, default=False),
        sa.Column('undone_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_timeline_changes_user_id', 'timeline_changes', ['user_id'])


def downgrade() -> None:
    op.drop_table('timeline_changes')
    op.drop_table('scheduled_blocks')
    op.drop_table('safety_policies')
    op.drop_table('intent_hypotheses')
    op.drop_table('human_states')
    op.drop_table('users')
