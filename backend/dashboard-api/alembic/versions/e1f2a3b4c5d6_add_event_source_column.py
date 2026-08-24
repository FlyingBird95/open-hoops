"""add event source column

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-08-16 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    source_enum = sa.Enum("analysis", "manual", name="eventsource")
    source_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "game_events",
        sa.Column("source", source_enum, nullable=False, server_default="analysis"),
    )


def downgrade() -> None:
    op.drop_column("game_events", "source")
    sa.Enum("analysis", "manual", name="eventsource").drop(op.get_bind(), checkfirst=True)
