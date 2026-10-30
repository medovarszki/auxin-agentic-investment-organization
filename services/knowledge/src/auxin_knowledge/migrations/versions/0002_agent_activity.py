"""agent activity (live LLM steps)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30 19:45:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('agent_activity',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('agent', sa.Text(), nullable=False),
    sa.Column('task_id', sa.Text(), nullable=True),
    sa.Column('trace_id', sa.Text(), nullable=True),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('is_error', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_activity_created_at'), 'agent_activity', ['created_at'], unique=False)
    op.create_index(op.f('ix_agent_activity_task_id'), 'agent_activity', ['task_id'], unique=False)
    op.create_index(op.f('ix_agent_activity_trace_id'), 'agent_activity', ['trace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agent_activity_trace_id'), table_name='agent_activity')
    op.drop_index(op.f('ix_agent_activity_task_id'), table_name='agent_activity')
    op.drop_index(op.f('ix_agent_activity_created_at'), table_name='agent_activity')
    op.drop_table('agent_activity')
