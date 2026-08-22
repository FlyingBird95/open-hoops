"""Factory Boy factories for backend test data."""

import datetime

import factory

from open_hoops.service.event.models import EventSource, GameEvent
from open_hoops.service.game.models import Game, GameFile, GameStatus
from open_hoops.service.player.models import Player
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats
from open_hoops.service.team.models import Team


class TeamFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Team
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"Team {n}")
    is_own = False
    home_color = "#000000"
    away_color = "#ffffff"


class PlayerFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Player
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    jersey_number = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Player {n}")
    team = factory.SubFactory(TeamFactory)


class GameFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Game
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"Game {n}")
    date = factory.LazyFunction(lambda: datetime.date(2026, 8, 10))
    status = GameStatus.pending
    own_team = factory.SubFactory(TeamFactory, is_own=True)
    opponent_team = factory.SubFactory(TeamFactory, is_own=False)


class GameFileFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = GameFile
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    game = factory.SubFactory(GameFactory)
    file_path = factory.Sequence(lambda n: f"uploads/part{n}.mp4")
    position = factory.Sequence(lambda n: n)
    original_filename = factory.Sequence(lambda n: f"part{n}.mp4")
    size_bytes = 1000


class GameTeamStatsFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = GameTeamStats
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    game = factory.SubFactory(GameFactory)
    team = factory.SubFactory(TeamFactory)
    score = 0
    possession_pct = 50.0


class GamePlayerStatsFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = GamePlayerStats
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    game = factory.SubFactory(GameFactory)
    team = factory.SubFactory(TeamFactory)
    player = factory.SubFactory(PlayerFactory)
    jersey_number = factory.LazyAttribute(lambda o: o.player.jersey_number)
    distance_covered_m = 0.0
    shot_attempts = 0
    shot_makes = 0
    passes_made = 0
    passes_received = 0
    possession_frames = 0


class GameEventFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = GameEvent
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    game = factory.SubFactory(GameFactory)
    type = "shot"
    frame = factory.Sequence(lambda n: n * 30)
    timestamp_sec = factory.Sequence(lambda n: float(n))
    source = EventSource.manual
