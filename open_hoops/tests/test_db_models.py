"""Tests for open_hoops.service models — relationships, defaults, constraints."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from open_hoops.core.database import Base
from open_hoops.service.event.models import EventSource, GameEvent
from open_hoops.service.game.models import Game, GameFile, GameStatus
from open_hoops.service.player.models import Player
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats
from open_hoops.service.team.models import Team, generate_uid

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    session = Session()
    yield session
    session.close()


@pytest.fixture
def home_team(db):
    team = Team(uid=generate_uid(), name="Lakers", is_own=True)
    db.add(team)
    db.commit()
    return team


@pytest.fixture
def away_team(db):
    team = Team(uid=generate_uid(), name="Celtics", is_own=False)
    db.add(team)
    db.commit()
    return team


@pytest.fixture
def player(db, home_team):
    p = Player(uid=generate_uid(), jersey_number=23, name="LeBron", team_id=home_team.id)
    db.add(p)
    db.commit()
    return p


@pytest.fixture
def game(db, home_team, away_team):
    g = Game(
        uid=generate_uid(),
        name="Finals G1",
        date=datetime.date(2026, 6, 1),
        own_team_id=home_team.id,
        opponent_team_id=away_team.id,
    )
    db.add(g)
    db.commit()
    return g


def test_generate_uid_format():
    uid = generate_uid()
    assert len(uid) == 32
    assert uid.isalnum()
    assert uid == uid.lower()


def test_generate_uid_uniqueness():
    uids = {generate_uid() for _ in range(100)}
    assert len(uids) == 100


def test_team_defaults(db):
    team = Team(uid=generate_uid(), name="Test")
    db.add(team)
    db.commit()
    db.refresh(team)

    assert team.is_own is False
    assert team.home_color == "#000000"
    assert team.away_color == "#ffffff"


def test_team_player_relationship(db, home_team):
    p1 = Player(uid=generate_uid(), jersey_number=23, name="LeBron", team_id=home_team.id)
    p2 = Player(uid=generate_uid(), jersey_number=3, name="AD", team_id=home_team.id)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(home_team)

    assert len(home_team.players) == 2
    assert p1.team.uid == home_team.uid


def test_team_cascade_delete_players(db):
    team = Team(uid=generate_uid(), name="Temp")
    db.add(team)
    db.flush()
    db.add(Player(uid=generate_uid(), jersey_number=1, team_id=team.id))
    db.commit()

    db.delete(team)
    db.commit()
    assert db.query(Player).count() == 0


def test_game_defaults(game, db):
    db.refresh(game)
    assert game.status == GameStatus.pending
    assert game.duration_seconds == 0.0
    assert game.fps == 0.0
    assert game.is_archived is False
    assert game.own_team_color == "#000000"
    assert game.opponent_team_color == "#ffffff"


def test_game_team_relationships(game, home_team, away_team, db):
    db.refresh(game)
    assert game.own_team.name == "Lakers"
    assert game.opponent_team.name == "Celtics"


def test_game_file_unique_constraint(db, game):
    db.add(
        GameFile(
            uid=generate_uid(),
            game_id=game.id,
            file_path="a.mp4",
            position=0,
            original_filename="a.mp4",
            size_bytes=100,
        )
    )
    db.add(
        GameFile(
            uid=generate_uid(),
            game_id=game.id,
            file_path="b.mp4",
            position=0,
            original_filename="b.mp4",
            size_bytes=100,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_game_cascade_delete(db, game, home_team):
    db.add(GameTeamStats(game_id=game.id, team_id=home_team.id, score=50))
    db.add(
        GamePlayerStats(game_id=game.id, team_id=home_team.id, jersey_number=5, shot_attempts=10)
    )
    db.add(
        GameEvent(
            game_id=game.id, type="shot", frame=100, timestamp_sec=3.3, source=EventSource.manual
        )
    )
    db.add(
        GameFile(
            uid=generate_uid(),
            game_id=game.id,
            file_path="x.mp4",
            position=0,
            original_filename="x.mp4",
            size_bytes=500,
        )
    )
    db.commit()

    db.delete(game)
    db.commit()

    assert db.query(GameTeamStats).count() == 0
    assert db.query(GamePlayerStats).count() == 0
    assert db.query(GameEvent).count() == 0
    assert db.query(GameFile).count() == 0


def test_game_event_source_default(db, game):
    event = GameEvent(game_id=game.id, type="pass", frame=50, timestamp_sec=1.5)
    db.add(event)
    db.commit()
    db.refresh(event)

    assert event.source == EventSource.analysis


def test_uid_unique_constraint(db):
    uid = generate_uid()
    db.add(Team(uid=uid, name="First"))
    db.commit()
    db.add(Team(uid=uid, name="Duplicate"))
    with pytest.raises(IntegrityError):
        db.commit()
