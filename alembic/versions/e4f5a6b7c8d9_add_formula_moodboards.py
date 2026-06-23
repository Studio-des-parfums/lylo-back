"""add formula moodboards

Revision ID: e4f5a6b7c8d9
Revises: b7c8d9e0f1a2
Create Date: 2026-06-23 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generated_formulas", sa.Column("moodboard_notes_key", sa.String(length=64), nullable=True))
    op.add_column("generated_formulas", sa.Column("moodboard_image_url", sa.String(length=500), nullable=True))
    op.create_index(op.f("ix_generated_formulas_moodboard_notes_key"), "generated_formulas", ["moodboard_notes_key"], unique=False)

    op.create_table(
        "formula_moodboards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notes_key", sa.String(length=64), nullable=False),
        sa.Column("top_notes", sa.JSON(), nullable=False),
        sa.Column("heart_notes", sa.JSON(), nullable=False),
        sa.Column("base_notes", sa.JSON(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("cloudinary_public_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_formula_moodboards_id"), "formula_moodboards", ["id"], unique=False)
    op.create_index(op.f("ix_formula_moodboards_notes_key"), "formula_moodboards", ["notes_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_formula_moodboards_notes_key"), table_name="formula_moodboards")
    op.drop_index(op.f("ix_formula_moodboards_id"), table_name="formula_moodboards")
    op.drop_table("formula_moodboards")

    op.drop_index(op.f("ix_generated_formulas_moodboard_notes_key"), table_name="generated_formulas")
    op.drop_column("generated_formulas", "moodboard_image_url")
    op.drop_column("generated_formulas", "moodboard_notes_key")
