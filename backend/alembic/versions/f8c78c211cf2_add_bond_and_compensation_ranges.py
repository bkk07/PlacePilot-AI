"""add bond and compensation ranges

Revision ID: f8c78c211cf2
Revises: 42149776437b
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f8c78c211cf2'
down_revision: Union[str, None] = '1756dd775441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('job_positions', sa.Column('bond_required', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('job_positions', sa.Column('bond_duration_months', sa.Integer(), nullable=True))
    op.add_column('job_positions', sa.Column('bond_amount', sa.Numeric(12, 2), nullable=True))
    op.add_column('job_positions', sa.Column('bond_description', sa.Text(), nullable=True))
    op.add_column('compensations', sa.Column('ctc_min', sa.Numeric(12, 2), nullable=True))
    op.add_column('compensations', sa.Column('ctc_max', sa.Numeric(12, 2), nullable=True))
    op.add_column('compensations', sa.Column('stipend_min', sa.Numeric(12, 2), nullable=True))
    op.add_column('compensations', sa.Column('stipend_max', sa.Numeric(12, 2), nullable=True))
    op.add_column('compensations', sa.Column('is_unpaid', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('compensations', sa.Column('stipend_type', sa.String(), nullable=True))
    op.add_column('internship_details', sa.Column('stipend_min', sa.Numeric(12, 2), nullable=True))
    op.add_column('internship_details', sa.Column('stipend_max', sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('internship_details', 'stipend_max')
    op.drop_column('internship_details', 'stipend_min')
    op.drop_column('compensations', 'stipend_type')
    op.drop_column('compensations', 'is_unpaid')
    op.drop_column('compensations', 'stipend_max')
    op.drop_column('compensations', 'stipend_min')
    op.drop_column('compensations', 'ctc_max')
    op.drop_column('compensations', 'ctc_min')
    op.drop_column('job_positions', 'bond_description')
    op.drop_column('job_positions', 'bond_amount')
    op.drop_column('job_positions', 'bond_duration_months')
    op.drop_column('job_positions', 'bond_required')
