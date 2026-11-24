"""rename formula_moodboards.cloudinary_public_id to storage_key

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""
from typing import Sequence, Union

from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("formula_moodboards", "cloudinary_public_id", new_column_name="storage_key")


def downgrade() -> None:
    op.alter_column("formula_moodboards", "storage_key", new_column_name="cloudinary_public_id")
