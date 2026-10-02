"""add translation_group_id to questions and question_choices

Revision ID: a3b4c5d6e7f8
Revises: 339cc625be54
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = '339cc625be54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('questions', sa.Column('translation_group_id', sa.String(length=36), nullable=True))
    op.create_index('ix_questions_translation_group_id', 'questions', ['translation_group_id'])
    op.add_column('question_choices', sa.Column('translation_group_id', sa.String(length=36), nullable=True))
    op.create_index('ix_question_choices_translation_group_id', 'question_choices', ['translation_group_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_question_choices_translation_group_id', table_name='question_choices')
    op.drop_column('question_choices', 'translation_group_id')
    op.drop_index('ix_questions_translation_group_id', table_name='questions')
    op.drop_column('questions', 'translation_group_id')
