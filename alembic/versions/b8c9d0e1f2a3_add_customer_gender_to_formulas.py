"""add generated_formulas.customer_gender / customer_first_name

Genre déclaré à l'agent en début de session vocale (« masculin » / « féminin ») : sert à la
civilité (Monsieur / Madame) du mail « Recevoir par mail ». Prénom stocké à part pour la page
/formulas (customer_name concatène prénom + nom).

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generated_formulas", sa.Column("customer_gender", sa.String(20), nullable=True))
    op.add_column("generated_formulas", sa.Column("customer_first_name", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("generated_formulas", "customer_first_name")
    op.drop_column("generated_formulas", "customer_gender")
