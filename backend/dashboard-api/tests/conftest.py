from app.database import database
from app.main import app
from pytest_factoryboy import LazyFixture, register
from testhelpers.db import ScopedSession
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


def _override_use_session():
    session = ScopedSession()
    yield session


app.dependency_overrides[database.use_session] = _override_use_session
