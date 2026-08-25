"""Factory Boy factories for test data — shared across all test suites."""

import datetime

import factory
from open_hoops.service.event.models import EventSource, GameEvent
from open_hoops.service.game.models import Game, GameFile, GameStatus
from open_hoops.service.player.models import Player
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats
from open_hoops.service.team.models import Team


class ModelFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"


class TeamFactory(ModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: f"Team {n}")
    is_own = False
    home_color = "#000000"
    away_color = "#ffffff"


class PlayerFactory(ModelFactory):
    class Meta:
        model = Player

    jersey_number = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Player {n}")
    team = factory.SubFactory(TeamFactory)


class GameFactory(ModelFactory):
    class Meta:
        model = Game

    name = factory.Sequence(lambda n: f"Game {n}")
    date = factory.LazyFunction(lambda: datetime.date(2026, 8, 10))
    status = GameStatus.pending
    own_team = factory.SubFactory(TeamFactory, is_own=True)
    opponent_team = factory.SubFactory(TeamFactory, is_own=False)

    @factory.post_generation
    def files(obj, create, extracted, **kwargs):
        pass

    @factory.post_generation
    def events(obj, create, extracted, **kwargs):
        pass


class GameFileFactory(ModelFactory):
    class Meta:
        model = GameFile

    game = factory.SubFactory(GameFactory)
    file_path = factory.Sequence(lambda n: f"uploads/part{n}.mp4")
    position = factory.Sequence(lambda n: n)
    original_filename = factory.Sequence(lambda n: f"part{n}.mp4")
    size_bytes = 1000


class GameTeamStatsFactory(ModelFactory):
    class Meta:
        model = GameTeamStats

    game = factory.SubFactory(GameFactory)
    team = factory.SubFactory(TeamFactory)
    score = 0
    possession_pct = 50.0


class GamePlayerStatsFactory(ModelFactory):
    class Meta:
        model = GamePlayerStats

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


class GameEventFactory(ModelFactory):
    class Meta:
        model = GameEvent

    game = factory.SubFactory(GameFactory)
    type = "shot"
    frame = factory.Sequence(lambda n: n * 30)
    timestamp_sec = factory.Sequence(lambda n: float(n))
    source = EventSource.manual
