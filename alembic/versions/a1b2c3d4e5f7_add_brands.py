"""add brands table + question_groups.brand (un seul questionnaire actif par marque)

Revision ID: a1b2c3d4e5f7
Revises: b4c5d6e7f8a9
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("slug", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("INSERT INTO brands (slug, name) VALUES ('lylo', 'Lylo'), ('ester', 'Ester')")

    op.add_column(
        "question_groups",
        sa.Column("brand", sa.String(20), nullable=False, server_default="lylo"),
    )
    op.create_foreign_key(
        "fk_question_groups_brand", "question_groups", "brands",
        ["brand"], ["slug"], onupdate="CASCADE", ondelete="RESTRICT",
    )
    op.create_index("ix_question_groups_brand", "question_groups", ["brand"])
    # Nom unique par marque (et non plus globalement) : deux marques peuvent avoir "Questionnaire 1".
    op.drop_constraint("question_groups_name_key", "question_groups", type_="unique")
    op.create_unique_constraint("uq_question_groups_brand_name", "question_groups", ["brand", "name"])
    # S'il y a plusieurs groupes actifs pour une même marque, on ne garde que le plus ancien.
    op.execute(
        """
        UPDATE question_groups SET is_active = false
        WHERE is_active AND id NOT IN (
            SELECT MIN(id) FROM question_groups WHERE is_active GROUP BY brand
        )
        """
    )
    op.create_index(
        "uq_question_groups_one_active_per_brand",
        "question_groups",
        ["brand"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_question_groups_one_active_per_brand", table_name="question_groups")
    op.drop_constraint("uq_question_groups_brand_name", "question_groups", type_="unique")
    op.create_unique_constraint("question_groups_name_key", "question_groups", ["name"])
    op.drop_index("ix_question_groups_brand", table_name="question_groups")
    op.drop_constraint("fk_question_groups_brand", "question_groups", type_="foreignkey")
    op.drop_column("question_groups", "brand")
    op.drop_table("brands")
