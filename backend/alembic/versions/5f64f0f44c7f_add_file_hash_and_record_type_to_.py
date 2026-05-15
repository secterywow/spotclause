"""add file_hash and record_type to contract_records

Revision ID: 5f64f0f44c7f
Revises: 0afb4f79b107
Create Date: 2026-05-15 09:53:26.518440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f64f0f44c7f'
down_revision: Union[str, None] = '0afb4f79b107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contract_records', sa.Column('file_hash', sa.String(64), nullable=True))
    op.create_index('ix_contract_records_file_hash', 'contract_records', ['file_hash'])


def downgrade() -> None:
    op.drop_index('ix_contract_records_file_hash', table_name='contract_records')
    op.drop_column('contract_records', 'file_hash')
