"""add generated_formulas.customer_company / customer_job_title

Coordonnées optionnelles saisies dans la modale "Recevoir par mail".

Revision ID: a7b8c9d0e1f2
Revises: e5f6a7b8c9d0
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generated_formulas", sa.Column("customer_company", sa.String(200), nullable=True))
    op.add_column("generated_formulas", sa.Column("customer_job_title", sa.String(150), nullable=True))


def downgrade() -> None:
    op.drop_column("generated_formulas", "customer_job_title")
    op.drop_column("generated_formulas", "customer_company")
