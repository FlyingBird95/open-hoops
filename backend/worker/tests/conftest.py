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
register(PlayerFactory, team=LazyFixture("own_team"), jersey_number=23, name="Star")
register(GameFactory, own_team=LazyFixture("own_team"), opponent_team=LazyFixture("opponent_team"))
register(GameFileFactory, game=LazyFixture("game"))
register(GameTeamStatsFactory, game=LazyFixture("game"))
register(GamePlayerStatsFactory, game=LazyFixture("game"))
register(GameEventFactory, game=LazyFixture("game"))
