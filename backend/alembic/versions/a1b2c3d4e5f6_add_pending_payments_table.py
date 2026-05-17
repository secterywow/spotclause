"""add pending_payments table

Revision ID: a1b2c3d4e5f6
Revises: 5f64f0f44c7f
Create Date: 2026-05-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5f64f0f44c7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pending_payments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan', sa.Enum('standard', 'pro', name='pending_plan'), nullable=False),
        sa.Column('billing_cycle', sa.Enum('monthly', 'yearly', name='pending_cycle'), nullable=False),
        sa.Column('checkout_session_id', sa.String(255), unique=True, nullable=True),
        sa.Column('status', sa.Enum('pending', 'completed', 'failed', name='pending_status'), default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pending_payments_checkout_session_id', 'pending_payments', ['checkout_session_id'])
    op.create_index('ix_pending_payments_status', 'pending_payments', ['status'])


def downgrade() -> None:
    op.drop_index('ix_pending_payments_status', table_name='pending_payments')
    op.drop_index('ix_pending_payments_checkout_session_id', table_name='pending_payments')
    op.drop_table('pending_payments')
    op.execute('DROP TYPE IF EXISTS pending_plan')
    op.execute('DROP TYPE IF EXISTS pending_cycle')
    op.execute('DROP TYPE IF EXISTS pending_status')
