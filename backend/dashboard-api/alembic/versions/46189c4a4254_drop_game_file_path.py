"""drop file_path from games, migrate data to game_files

Revision ID: 46189c4a4254
Revises: 7d8e88e9a630
Create Date: 2026-08-05 00:00:00.000000

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "46189c4a4254"
down_revision: Union[str, None] = "7d8e88e9a630"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Data migration: copy file_path to game_files for games that have no GameFile rows yet
    games = conn.execute(
        sa.text(
            "SELECT id, uid, file_path FROM games WHERE file_path != '' AND file_path IS NOT NULL"
        )
    )
    for game in games:
        existing = conn.execute(
            sa.text("SELECT COUNT(*) FROM game_files WHERE game_id = :gid"),
            {"gid": game.id},
        ).scalar()
        if existing == 0:
            uid = uuid.uuid4().hex
            conn.execute(
                sa.text(
                    "INSERT INTO game_files (uid, game_id, file_path, position, original_filename, size_bytes) "
                    "VALUES (:uid, :gid, :path, 0, :fname, 0)"
                ),
                {
                    "uid": uid,
                    "gid": game.id,
                    "path": game.file_path,
                    "fname": game.file_path.split("/")[-1],
                },
            )

    # Schema migration: drop the file_path column from games
    op.drop_column("games", "file_path")


def downgrade() -> None:
    op.add_column(
        "games",
        sa.Column("file_path", sa.String(length=1024), nullable=False, server_default=""),
    )
