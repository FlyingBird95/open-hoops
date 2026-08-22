from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from open_hoops.db.base import Base

if TYPE_CHECKING:
    from open_hoops.db.service.player.models import Player


def generate_uid() -> str:
    return uuid.uuid4().hex


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    name: Mapped[str] = mapped_column(String(255))

    is_own: Mapped[bool] = mapped_column(Boolean, default=False)
    """Whether this is the user's own team (vs an opponent)."""

    home_color: Mapped[str] = mapped_column(String(7), default="#000000")
    """Primary jersey color as hex."""

    away_color: Mapped[str] = mapped_column(String(7), default="#ffffff")
    """Secondary/away jersey color as hex."""

    players: Mapped[list[Player]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    """All players belonging to this team."""
