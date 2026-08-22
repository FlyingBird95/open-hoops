"""add uid to game_team_stats, game_player_stats, game_events

Revision ID: b3c4d5e6f7a8
Revises: d1a9ec1b04e5
Create Date: 2026-08-22 10:00:00.000000

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "d1a9ec1b04e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("game_team_stats", sa.Column("uid", sa.String(32), nullable=True))
    op.add_column("game_player_stats", sa.Column("uid", sa.String(32), nullable=True))
    op.add_column("game_events", sa.Column("uid", sa.String(32), nullable=True))

    conn = op.get_bind()
    for table in ("game_team_stats", "game_player_stats", "game_events"):
        rows = conn.execute(sa.text(f"SELECT id FROM {table}")).fetchall()
        for (row_id,) in rows:
            uid = uuid.uuid4().hex
            conn.execute(sa.text(f"UPDATE {table} SET uid = :uid WHERE id = :id"), {"uid": uid, "id": row_id})

    op.alter_column("game_team_stats", "uid", nullable=False)
    op.alter_column("game_player_stats", "uid", nullable=False)
    op.alter_column("game_events", "uid", nullable=False)

    op.create_unique_constraint("uq_game_team_stats_uid", "game_team_stats", ["uid"])
    op.create_unique_constraint("uq_game_player_stats_uid", "game_player_stats", ["uid"])
    op.create_unique_constraint("uq_game_events_uid", "game_events", ["uid"])


def downgrade() -> None:
    op.drop_constraint("uq_game_events_uid", "game_events", type_="unique")
    op.drop_constraint("uq_game_player_stats_uid", "game_player_stats", type_="unique")
    op.drop_constraint("uq_game_team_stats_uid", "game_team_stats", type_="unique")

    op.drop_column("game_events", "uid")
    op.drop_column("game_player_stats", "uid")
    op.drop_column("game_team_stats", "uid")
