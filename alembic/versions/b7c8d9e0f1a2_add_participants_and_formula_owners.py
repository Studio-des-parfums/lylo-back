"""add_participants_and_formula_owners

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "d7f8e9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("gender", sa.String(length=30), nullable=True),
        sa.Column("age", sa.String(length=30), nullable=True),
        sa.Column("has_allergies", sa.String(length=10), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_participants_email"), "participants", ["email"], unique=True)
    op.create_index(op.f("ix_participants_id"), "participants", ["id"], unique=False)

    op.add_column("generated_formulas", sa.Column("participant_id", sa.Integer(), nullable=True))
    op.add_column("generated_formulas", sa.Column("owner_type", sa.String(length=20), nullable=True))
    op.add_column("generated_formulas", sa.Column("owner_team_id", sa.Integer(), nullable=True))
    op.add_column("generated_formulas", sa.Column("owner_customer_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_generated_formulas_participant_id"), "generated_formulas", ["participant_id"], unique=False)
    op.create_index(op.f("ix_generated_formulas_owner_team_id"), "generated_formulas", ["owner_team_id"], unique=False)
    op.create_index(op.f("ix_generated_formulas_owner_customer_id"), "generated_formulas", ["owner_customer_id"], unique=False)
    op.create_foreign_key(
        "fk_generated_formulas_participant_id_participants",
        "generated_formulas",
        "participants",
        ["participant_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_generated_formulas_owner_team_id_teams",
        "generated_formulas",
        "teams",
        ["owner_team_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_generated_formulas_owner_customer_id_customers",
        "generated_formulas",
        "customers",
        ["owner_customer_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_generated_formulas_owner_customer_id_customers", "generated_formulas", type_="foreignkey")
    op.drop_constraint("fk_generated_formulas_owner_team_id_teams", "generated_formulas", type_="foreignkey")
    op.drop_constraint("fk_generated_formulas_participant_id_participants", "generated_formulas", type_="foreignkey")
    op.drop_index(op.f("ix_generated_formulas_owner_customer_id"), table_name="generated_formulas")
    op.drop_index(op.f("ix_generated_formulas_owner_team_id"), table_name="generated_formulas")
    op.drop_index(op.f("ix_generated_formulas_participant_id"), table_name="generated_formulas")
    op.drop_column("generated_formulas", "owner_customer_id")
    op.drop_column("generated_formulas", "owner_team_id")
    op.drop_column("generated_formulas", "owner_type")
    op.drop_column("generated_formulas", "participant_id")

    op.drop_index(op.f("ix_participants_id"), table_name="participants")
    op.drop_index(op.f("ix_participants_email"), table_name="participants")
    op.drop_table("participants")
