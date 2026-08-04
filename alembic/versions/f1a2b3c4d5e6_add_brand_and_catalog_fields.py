"""add brand and catalog fields to generated_formulas

Revision ID: f1a2b3c4d5e6
Revises: e4f5a6b7c8d9
Create Date: 2026-08-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generated_formulas", sa.Column("brand", sa.String(length=20), nullable=True, server_default="lylo"))
    op.add_column("generated_formulas", sa.Column("source", sa.String(length=20), nullable=True, server_default="generated"))
    op.add_column("generated_formulas", sa.Column("catalog_brand", sa.String(length=100), nullable=True))
    op.add_column("generated_formulas", sa.Column("catalog_perfume_name", sa.String(length=200), nullable=True))
    op.add_column("generated_formulas", sa.Column("match_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("generated_formulas", "match_reason")
    op.drop_column("generated_formulas", "catalog_perfume_name")
    op.drop_column("generated_formulas", "catalog_brand")
    op.drop_column("generated_formulas", "source")
    op.drop_column("generated_formulas", "brand")
