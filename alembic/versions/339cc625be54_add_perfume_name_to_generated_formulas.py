"""add perfume_name to generated_formulas

Revision ID: 339cc625be54
Revises: f1a2b3c4d5e6
Create Date: 2026-09-30 15:38:19.623955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '339cc625be54'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('generated_formulas', sa.Column('perfume_name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('generated_formulas', 'perfume_name')
