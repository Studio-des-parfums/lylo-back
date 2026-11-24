"""add answer format to question_groups

Revision ID: c2d3e4f5a6b7
Revises: a1b2c3d4e5f7
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None

# Valeurs par défaut = format historique (2 favoris + 2 moins aimés, justifiés).
# Libellés {langue: texte} ; NULL = libellés par défaut (« Vos préférés » / « Les moins aimés »).
# JSONB (et non JSON) : les requêtes sur question_groups utilisent DISTINCT.
_COLUMNS = [
    sa.Column("positive_label", JSONB, nullable=True),
    sa.Column("negative_label", JSONB, nullable=True),
    sa.Column("positive_count", sa.Integer, nullable=False, server_default="2"),
    sa.Column("positive_justify", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.Column("negative_count", sa.Integer, nullable=False, server_default="2"),
    sa.Column("negative_justify", sa.Boolean, nullable=False, server_default=sa.true()),
]


def upgrade() -> None:
    for column in _COLUMNS:
        op.add_column("question_groups", column)
    op.create_check_constraint(
        "ck_question_groups_answer_format",
        "question_groups",
        "positive_count BETWEEN 1 AND 3 AND negative_count BETWEEN 0 AND 3",
    )


def downgrade() -> None:
    op.drop_constraint("ck_question_groups_answer_format", "question_groups", type_="check")
    for column in reversed(_COLUMNS):
        op.drop_column("question_groups", column.name)
