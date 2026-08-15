import uuid
from datetime import date

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

from open_hoops.db.base import Base

import enum


class GameStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


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

    players: Mapped[list["Player"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    """All players belonging to this team."""


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    jersey_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    team: Mapped["Team"] = relationship(back_populates="players")
    """The team this player belongs to."""


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
    """Analysis pipeline status: pending → processing → done | failed."""

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


class GameTeamStats(Base):
    __tablename__ = "game_team_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[int] = mapped_column(Integer, default=0)

    possession_pct: Mapped[float] = mapped_column(Float, default=0.0)
    """Percentage of total game time this team had possession."""

    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    game: Mapped["Game"] = relationship(back_populates="team_stats")
    """The game these stats belong to."""

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    team: Mapped["Team"] = relationship()
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
    game: Mapped["Game"] = relationship(back_populates="player_stats")
    """The game these stats belong to."""

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    team: Mapped["Team"] = relationship()
    """The team this player was on during this game."""

    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    player: Mapped["Player | None"] = relationship()
    """The player (if matched to a roster entry)."""


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50))
    frame: Mapped[int] = mapped_column(Integer)

    timestamp_sec: Mapped[float] = mapped_column(Float)
    """Event time in seconds from video start."""

    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    game: Mapped["Game"] = relationship(back_populates="events")
    """The game this event occurred in."""

    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    player: Mapped["Player | None"] = relationship()
    """The player involved in this event (if applicable)."""

    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    team: Mapped["Team | None"] = relationship()
    """The team involved in this event (if applicable)."""

    bbox_x1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_y1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_x2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_y2: Mapped[int | None] = mapped_column(Integer, nullable=True)
