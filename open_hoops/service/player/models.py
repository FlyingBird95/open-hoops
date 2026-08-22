from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from open_hoops.core.database import Base
from open_hoops.service.team.models import generate_uid

if TYPE_CHECKING:
    from open_hoops.service.team.models import Team


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    jersey_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    team: Mapped["Team"] = relationship(back_populates="players")
    """The team this player belongs to."""
