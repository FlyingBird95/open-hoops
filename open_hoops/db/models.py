import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Integer, String
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
    home_color: Mapped[str] = mapped_column(String(7), default="#000000")
    away_color: Mapped[str] = mapped_column(String(7), default="#ffffff")

    players: Mapped[list["Player"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    jersey_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    team: Mapped["Team"] = relationship(back_populates="players")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(String(1024))
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    home_team_color: Mapped[str] = mapped_column(String(7), default="#000000")
    away_team_color: Mapped[str] = mapped_column(String(7), default="#ffffff")
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus), default=GameStatus.pending)

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
    team_stats: Mapped[list["GameTeamStats"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    player_stats: Mapped[list["GamePlayerStats"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    events: Mapped[list["GameEvent"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )


class GameTeamStats(Base):
    __tablename__ = "game_team_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    possession_pct: Mapped[float] = mapped_column(Float, default=0.0)

    game: Mapped["Game"] = relationship(back_populates="team_stats")
    team: Mapped["Team"] = relationship()


class GamePlayerStats(Base):
    __tablename__ = "game_player_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_covered_m: Mapped[float] = mapped_column(Float, default=0.0)
    shot_attempts: Mapped[int] = mapped_column(Integer, default=0)
    shot_makes: Mapped[int] = mapped_column(Integer, default=0)
    passes_made: Mapped[int] = mapped_column(Integer, default=0)
    passes_received: Mapped[int] = mapped_column(Integer, default=0)
    possession_frames: Mapped[int] = mapped_column(Integer, default=0)

    game: Mapped["Game"] = relationship(back_populates="player_stats")
    team: Mapped["Team"] = relationship()
    player: Mapped["Player | None"] = relationship()


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    type: Mapped[str] = mapped_column(String(50))
    frame: Mapped[int] = mapped_column(Integer)
    timestamp_sec: Mapped[float] = mapped_column(Float)
    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)

    game: Mapped["Game"] = relationship(back_populates="events")
    player: Mapped["Player | None"] = relationship()
    team: Mapped["Team | None"] = relationship()
