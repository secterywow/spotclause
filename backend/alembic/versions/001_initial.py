"""Initial migration - create all tables

Revision ID: 001
Revises:
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100)),
        sa.Column('avatar', sa.String(500)),
        sa.Column('auth_provider', sa.Enum('google', 'email', name='auth_provider'), nullable=False),
        sa.Column('google_id', sa.String(100), unique=True),
        sa.Column('password_hash', sa.String(255)),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('role', sa.Enum('user', 'admin', name='user_role'), default='user'),
        sa.Column('plan', sa.Enum('free', 'standard', 'pro', name='user_plan'), default='free'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('google_id'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Contract records table
    op.create_table(
        'contract_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(20)),
        sa.Column('contract_type', sa.String(50)),
        sa.Column('jurisdiction', sa.String(50)),
        sa.Column('overall_score', sa.Integer()),
        sa.Column('high_risk_count', sa.Integer(), default=0),
        sa.Column('medium_risk_count', sa.Integer(), default=0),
        sa.Column('low_risk_count', sa.Integer(), default=0),
        sa.Column('report_json', sa.Text()),
        sa.Column('messages_json', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_contract_records_user_id', 'contract_records', ['user_id'])

    # Contract messages table
    op.create_table(
        'contract_messages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('contract_record_id', sa.BigInteger(), sa.ForeignKey('contract_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('round', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', name='message_role'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_input', sa.Integer(), default=0),
        sa.Column('token_output', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_contract_messages_contract_round', 'contract_messages', ['contract_record_id', 'round'])

    # Usage tracking table
    op.create_table(
        'usage_tracking',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('month', sa.String(7), nullable=False),
        sa.Column('analyze_count', sa.Integer(), default=0),
        sa.Column('compare_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'month', name='uix_usage_user_month'),
    )

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(100)),
        sa.Column('plan', sa.Enum('standard', 'pro', name='subscription_plan'), nullable=False),
        sa.Column('billing_cycle', sa.Enum('monthly', 'yearly', name='billing_cycle'), nullable=False),
        sa.Column('status', sa.Enum('active', 'cancelled', 'past_due', name='subscription_status'), default='active'),
        sa.Column('current_period_start', sa.DateTime(timezone=True)),
        sa.Column('current_period_end', sa.DateTime(timezone=True)),
        sa.Column('cancel_at_period_end', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # Risk rules table
    op.create_table(
        'risk_rules',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('rule_id', sa.String(50), unique=True, nullable=False),
        sa.Column('contract_types', sa.JSON(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('standard_practice', sa.Text()),
        sa.Column('suggested_alternative', sa.Text()),
        sa.Column('legal_basis', sa.String(500)),
        sa.Column('severity', sa.Enum('high', 'medium', 'low', name='rule_severity'), nullable=False),
        sa.Column('keywords', sa.JSON()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_id'),
    )
    op.create_index('ix_risk_rules_category', 'risk_rules', ['category'])
    op.create_index('ix_risk_rules_severity', 'risk_rules', ['severity'])

    # Regional pricing table
    op.create_table(
        'regional_pricing',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('country_code', sa.String(2), unique=True, nullable=False),
        sa.Column('region_name', sa.String(100), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('free_plan', sa.JSON(), default={}),
        sa.Column('standard_monthly', sa.Numeric(10, 2), nullable=False),
        sa.Column('standard_yearly', sa.Numeric(10, 2), nullable=False),
        sa.Column('pro_monthly', sa.Numeric(10, 2), nullable=False),
        sa.Column('pro_yearly', sa.Numeric(10, 2), nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_regional_pricing_country_code', 'regional_pricing', ['country_code'])

    # LLM call logs table
    op.create_table(
        'llm_call_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger()),
        sa.Column('contract_record_id', sa.BigInteger()),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100)),
        sa.Column('prompt_tokens', sa.Integer(), default=0),
        sa.Column('completion_tokens', sa.Integer(), default=0),
        sa.Column('total_tokens', sa.Integer(), default=0),
        sa.Column('cost_usd', sa.Numeric(10, 6), default=0),
        sa.Column('latency_ms', sa.Integer(), default=0),
        sa.Column('status', sa.String(20), default='success'),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('llm_call_logs')
    op.drop_table('regional_pricing')
    op.drop_table('risk_rules')
    op.drop_table('subscriptions')
    op.drop_table('usage_tracking')
    op.drop_table('contract_messages')
    op.drop_table('contract_records')
    op.drop_table('users')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS auth_provider')
    op.execute('DROP TYPE IF EXISTS user_role')
    op.execute('DROP TYPE IF EXISTS user_plan')
    op.execute('DROP TYPE IF EXISTS message_role')
    op.execute('DROP TYPE IF EXISTS subscription_plan')
    op.execute('DROP TYPE IF EXISTS billing_cycle')
    op.execute('DROP TYPE IF EXISTS subscription_status')
    op.execute('DROP TYPE IF EXISTS rule_severity')
