from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from open_hoops.db.base import Base

if TYPE_CHECKING:
    from open_hoops.db.service.game.models import Game
    from open_hoops.db.service.player.models import Player
    from open_hoops.db.service.team.models import Team


class GameTeamStats(Base):
    __tablename__ = "game_team_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[int] = mapped_column(Integer, default=0)

    possession_pct: Mapped[float] = mapped_column(Float, default=0.0)
    """Percentage of total game time this team had possession."""

    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    game: Mapped[Game] = relationship(back_populates="team_stats")
    """The game these stats belong to."""

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    team: Mapped[Team] = relationship()
    """The team these stats are for."""


class GamePlayerStats(Base):
    __tablename__ = "game_player_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    distance_covered_m: Mapped[float] = mapped_column(Float, default=0.0)
    """Total distance covered in meters (from court position tracking)."""

    shot_attempts: Mapped[int] = mapped_column(Integer, default=0)
    shot_makes: Mapped[int] = mapped_column(Integer, default=0)
    passes_made: Mapped[int] = mapped_column(Integer, default=0)
    passes_received: Mapped[int] = mapped_column(Integer, default=0)

    possession_frames: Mapped[int] = mapped_column(Integer, default=0)
    """Number of frames this player was nearest to the ball."""

    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    game: Mapped[Game] = relationship(back_populates="player_stats")
    """The game these stats belong to."""

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    team: Mapped[Team] = relationship()
    """The team this player was on during this game."""

    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    player: Mapped[Player | None] = relationship()
    """The player (if matched to a roster entry)."""
