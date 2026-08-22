import pytest
from app.main import app
from pytest_factoryboy import register
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from open_hoops.core.database import Base, get_db

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


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Register factories — creates fixtures like `team`, `player`, `game`, etc.
register(TeamFactory)
register(PlayerFactory)
register(GameFactory)
register(GameFileFactory)
register(GameTeamStatsFactory)
register(GamePlayerStatsFactory)
register(GameEventFactory)


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = TestSession()
    # Wire up factories to use this session
    TeamFactory._meta.sqlalchemy_session = session
    PlayerFactory._meta.sqlalchemy_session = session
    GameFactory._meta.sqlalchemy_session = session
    GameFileFactory._meta.sqlalchemy_session = session
    GameTeamStatsFactory._meta.sqlalchemy_session = session
    GamePlayerStatsFactory._meta.sqlalchemy_session = session
    GameEventFactory._meta.sqlalchemy_session = session
    yield session
    session.close()
    Base.metadata.drop_all(engine)
