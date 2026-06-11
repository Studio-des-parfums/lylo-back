"""add question groups

Revision ID: d7f8e9a0b1c2
Revises: 2b4df84e4987
Create Date: 2026-06-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7f8e9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "2b4df84e4987"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_question_groups_id"), "question_groups", ["id"], unique=False)

    op.create_table(
        "question_group_links",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["question_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id", "group_id"),
        sa.UniqueConstraint("question_id", "group_id", name="uq_question_group_links_question_group"),
    )
    op.create_index(
        op.f("ix_question_group_links_group_id"),
        "question_group_links",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_group_links_question_id"),
        "question_group_links",
        ["question_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_question_group_links_question_id"), table_name="question_group_links")
    op.drop_index(op.f("ix_question_group_links_group_id"), table_name="question_group_links")
    op.drop_table("question_group_links")
    op.drop_index(op.f("ix_question_groups_id"), table_name="question_groups")
    op.drop_table("question_groups")
