"""add project logo

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-10-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_logo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_logo_id"), "project_logo", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_logo_id"), table_name="project_logo")
    op.drop_table("project_logo")
