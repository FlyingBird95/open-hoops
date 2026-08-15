"""add unique constraint game_id+position on game_files

Revision ID: 908e9ee8b313
Revises: c081b8f2b624
Create Date: 2026-08-16 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "908e9ee8b313"
down_revision: Union[str, None] = "c081b8f2b624"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_game_files_game_id_position", "game_files", ["game_id", "position"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_game_files_game_id_position", "game_files", type_="unique")
