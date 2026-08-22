"""Shared test database setup — import into each conftest.py."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from open_hoops.core.database import Base

from .factories import (
    GameEventFactory,
    GameFactory,
    GameFileFactory,
    GamePlayerStatsFactory,
    GameTeamStatsFactory,
    PlayerFactory,
    TeamFactory,
)

TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)

ALL_FACTORIES = [
    TeamFactory,
    PlayerFactory,
    GameFactory,
    GameFileFactory,
    GameTeamStatsFactory,
    GamePlayerStatsFactory,
    GameEventFactory,
]


def create_db_session() -> Session:
    """Create tables, wire factories, return session. Call drop_db_session after."""
    Base.metadata.create_all(engine)
    session = TestSession()
    for f in ALL_FACTORIES:
        f._meta.sqlalchemy_session = session
    return session


def drop_db_session(session: Session) -> None:
    session.close()
    Base.metadata.drop_all(engine)
