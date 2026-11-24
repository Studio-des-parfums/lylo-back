"""add brands.coffret_id : coffret de notes (dashboard SDP) utilisé par chaque marque

NULL = toutes les notes actives, tous coffrets confondus.

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pas de clé étrangère : les coffrets vivent dans la base MySQL du dashboard SDP.
    op.add_column("brands", sa.Column("coffret_id", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("brands", "coffret_id")
