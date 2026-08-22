import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from open_hoops.core.database import Base
from open_hoops.service.team.models import generate_uid

if TYPE_CHECKING:
    from open_hoops.service.team.models import Team
    from open_hoops.service.stats.models import GameTeamStats, GamePlayerStats
    from open_hoops.service.event.models import GameEvent


class GameStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date)

    own_team_color: Mapped[str] = mapped_column(String(7), default="#000000")
    """Jersey color worn by own team in this specific game."""

    opponent_team_color: Mapped[str] = mapped_column(String(7), default="#ffffff")
    """Jersey color worn by opponent in this specific game."""

    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    """Total video duration after analysis."""

    fps: Mapped[float] = mapped_column(Float, default=0.0)
    """Video frame rate detected during analysis."""

    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus), default=GameStatus.pending)
    """Analysis pipeline status: pending -> processing -> done | failed."""

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    own_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    own_team: Mapped["Team"] = relationship(foreign_keys=[own_team_id])
    """The user's own team playing in this game."""

    opponent_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    opponent_team: Mapped["Team"] = relationship(foreign_keys=[opponent_team_id])
    """The opposing team in this game."""

    team_stats: Mapped[list["GameTeamStats"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    """Per-team aggregate stats for this game."""

    player_stats: Mapped[list["GamePlayerStats"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    """Per-player stats for this game."""

    events: Mapped[list["GameEvent"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    """Chronological game events (shots, passes, possessions)."""

    files: Mapped[list["GameFile"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="GameFile.position"
    )
    """Uploaded video files for this game, ordered by position."""


class GameFile(Base):
    __tablename__ = "game_files"
    __table_args__ = (UniqueConstraint("game_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    file_path: Mapped[str] = mapped_column(String(1024))

    position: Mapped[int] = mapped_column(Integer, default=0)
    """Order of this file within the game's file list."""

    original_filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    game: Mapped["Game"] = relationship(back_populates="files")
    """The game this file belongs to."""
