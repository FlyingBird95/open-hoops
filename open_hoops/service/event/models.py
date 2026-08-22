import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from open_hoops.core.database import Base


class EventSource(str, enum.Enum):
    analysis = "analysis"
    manual = "manual"


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
    player: Mapped["Player | None"] = relationship(foreign_keys=[player_id])
    """Primary player: passer, shooter, fouler, etc."""

    player2_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    player2: Mapped["Player | None"] = relationship(foreign_keys=[player2_id])
    """Secondary player: pass receiver, assist recipient, etc."""

    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    team: Mapped["Team | None"] = relationship()
    """The team involved in this event (if applicable)."""

    source: Mapped[EventSource] = mapped_column(
        Enum(EventSource), default=EventSource.analysis, server_default="analysis"
    )

    bbox_x1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_y1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_x2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_y2: Mapped[int | None] = mapped_column(Integer, nullable=True)
