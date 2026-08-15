"""add bbox columns to game_events

Revision ID: d4e5f6a7b8c9
Revises: c081b8f2b624
Create Date: 2026-08-16 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c081b8f2b624"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("game_events", sa.Column("bbox_x1", sa.Integer(), nullable=True))
    op.add_column("game_events", sa.Column("bbox_y1", sa.Integer(), nullable=True))
    op.add_column("game_events", sa.Column("bbox_x2", sa.Integer(), nullable=True))
    op.add_column("game_events", sa.Column("bbox_y2", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("game_events", "bbox_y2")
    op.drop_column("game_events", "bbox_x2")
    op.drop_column("game_events", "bbox_y1")
    op.drop_column("game_events", "bbox_x1")
