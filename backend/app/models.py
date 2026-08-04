import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class VideoStatus(str, enum.Enum):
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

    players: Mapped[list["Player"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    jersey_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    team: Mapped["Team"] = relationship(back_populates="players")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(String(1024))
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    status: Mapped[VideoStatus] = mapped_column(Enum(VideoStatus), default=VideoStatus.pending)
    stats_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
