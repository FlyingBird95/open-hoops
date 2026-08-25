import pytest
from app.database import database
from app.main import app
from pytest_factoryboy import LazyFixture, register
from testhelpers.factories import (
    GameEventFactory,
    GameFactory,
    GameFileFactory,
    GamePlayerStatsFactory,
    GameTeamStatsFactory,
    PlayerFactory,
    TeamFactory,
)
from testhelpers.fixtures import db  # noqa: F401

register(TeamFactory)
register(TeamFactory, "own_team", is_own=True)
register(TeamFactory, "opponent_team", is_own=False)
register(PlayerFactory)
register(GameFactory, own_team=LazyFixture("own_team"), opponent_team=LazyFixture("opponent_team"))
register(GameFileFactory, game=LazyFixture("game"))
register(GameTeamStatsFactory, game=LazyFixture("game"))
register(GamePlayerStatsFactory, game=LazyFixture("game"))
register(GameEventFactory, game=LazyFixture("game"))


@pytest.fixture(autouse=True)
def _override_db_dependency(db):  # noqa: F811
    def override_use_session():
        yield db

    app.dependency_overrides[database.use_session] = override_use_session
    yield
    app.dependency_overrides.pop(database.use_session, None)
