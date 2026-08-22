"""merge game_files constraint and event columns

Revision ID: 03f611a985be
Revises: 908e9ee8b313, e1f2a3b4c5d6
Create Date: 2026-08-17 19:31:48.955697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03f611a985be'
down_revision: Union[str, None] = ('908e9ee8b313', 'e1f2a3b4c5d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
