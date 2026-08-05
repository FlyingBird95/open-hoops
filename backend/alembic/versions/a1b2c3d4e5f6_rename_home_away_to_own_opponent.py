"""rename home/away team columns to own/opponent

Revision ID: a1b2c3d4e5f6
Revises: 46189c4a4254
Create Date: 2026-08-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "46189c4a4254"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("games", "home_team_id", new_column_name="own_team_id")
    op.alter_column("games", "away_team_id", new_column_name="opponent_team_id")
    op.alter_column("games", "home_team_color", new_column_name="own_team_color")
    op.alter_column("games", "away_team_color", new_column_name="opponent_team_color")


def downgrade() -> None:
    op.alter_column("games", "own_team_id", new_column_name="home_team_id")
    op.alter_column("games", "opponent_team_id", new_column_name="away_team_id")
    op.alter_column("games", "own_team_color", new_column_name="home_team_color")
    op.alter_column("games", "opponent_team_color", new_column_name="away_team_color")
