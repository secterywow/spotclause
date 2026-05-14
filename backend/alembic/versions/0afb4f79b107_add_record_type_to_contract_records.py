"""add record_type to contract_records

Revision ID: 0afb4f79b107
Revises: 001
Create Date: 2026-05-13 19:04:49.844704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0afb4f79b107'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type in PostgreSQL first, then add the column.
    record_type_enum = postgresql.ENUM('analysis', 'comparison', name='record_type_enum')
    record_type_enum.create(op.get_bind())

    op.add_column(
        'contract_records',
        sa.Column('record_type', sa.Enum('analysis', 'comparison', name='record_type_enum'),
                  server_default='analysis', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('contract_records', 'record_type')
    record_type_enum = postgresql.ENUM('analysis', 'comparison', name='record_type_enum')
    record_type_enum.drop(op.get_bind())
