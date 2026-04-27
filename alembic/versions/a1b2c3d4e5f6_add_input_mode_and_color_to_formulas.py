"""add_input_mode_and_color_to_generated_formulas

Revision ID: a1b2c3d4e5f6
Revises: cdef3d9a2282
Create Date: 2026-04-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cdef3d9a2282'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generated_formulas', sa.Column('input_mode', sa.String(length=20), nullable=True))
    op.add_column('generated_formulas', sa.Column('participant_color', sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column('generated_formulas', 'participant_color')
    op.drop_column('generated_formulas', 'input_mode')
