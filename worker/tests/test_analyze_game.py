"""Tests for worker.tasks.analyze_game — single-file, error handling, stats/events persistence."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from open_hoops.service.event.models import EventSource, GameEvent
from open_hoops.service.game.models import Game, GameFile, GameStatus
from open_hoops.service.player.models import Player
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats
from open_hoops.service.team.models import Team, generate_uid
from open_hoops.models import GameStats, PlayerStats, TeamStats
from open_hoops.models import Video as OHVideo


def make_stats(
    duration=60.0,
    fps=30.0,
    home_score=10,
    away_score=8,
    events=None,
    players=None,
):
    home_players = players or [
        PlayerStats(
            player_id=23,
            team_id="team_a",
            distance_covered_m=1500.0,
            shot_attempts=5,
            shot_makes=3,
            passes_made=4,
            passes_received=6,
            possession_frames=200,
        )
    ]
    return GameStats(
        video=OHVideo(path="uploads/fake.mp4"),
        duration_seconds=duration,
        fps=fps,
        teams=[
            TeamStats(
                team_id="team_a", score=home_score, possession_pct=55.0, players=home_players
            ),
            TeamStats(team_id="team_b", score=away_score, possession_pct=45.0, players=[]),
        ],
        events=events or [],
    )


class _NoCloseSession:
    def __init__(self, s):
        self._s = s

    def __getattr__(self, name):
        return getattr(self._s, name)

    def close(self):
        pass


@pytest.fixture
def game_setup(db_session):
    """Create home/away teams, player, game with one file."""
    home = Team(uid=generate_uid(), name="Home", is_own=True)
    away = Team(uid=generate_uid(), name="Away", is_own=False)
    db_session.add_all([home, away])
    db_session.flush()

    player = Player(uid=generate_uid(), jersey_number=23, name="Star", team_id=home.id)
    db_session.add(player)
    db_session.flush()

    game = Game(
        uid=generate_uid(),
        name="Test Game",
        date=datetime.date(2026, 8, 10),
        own_team_id=home.id,
        opponent_team_id=away.id,
    )
    db_session.add(game)
    db_session.flush()

    db_session.add(
        GameFile(
            uid=generate_uid(),
            game_id=game.id,
            file_path="uploads/game.mp4",
            position=0,
            original_filename="game.mp4",
            size_bytes=1000,
        )
    )
    db_session.commit()

    return game, home, away, player


def test_analyze_single_file(db_session, game_setup):
    game, _home, _away, _player = game_setup
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats(duration=90.0, fps=30.0)

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)),
        patch("open_hoops.analyzer.OpenHoop", return_value=mock_oh),
    ):
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    db_session.refresh(game)
    assert game.status == GameStatus.done
    assert game.duration_seconds == 90.0
    assert game.fps == 30.0
    mock_oh.extract_stats.assert_called_once()


def test_analyze_writes_team_stats(db_session, game_setup):
    game, home, away, _player = game_setup
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats(home_score=25, away_score=20)

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)),
        patch("open_hoops.analyzer.OpenHoop", return_value=mock_oh),
    ):
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    team_stats = db_session.query(GameTeamStats).filter(GameTeamStats.game_id == game.id).all()
    assert len(team_stats) == 2

    home_stats = next(ts for ts in team_stats if ts.team_id == home.id)
    away_stats = next(ts for ts in team_stats if ts.team_id == away.id)
    assert home_stats.score == 25
    assert home_stats.possession_pct == 55.0
    assert away_stats.score == 20
    assert away_stats.possession_pct == 45.0


def test_analyze_writes_player_stats(db_session, game_setup):
    game, _home, _away, player = game_setup
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats()

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)),
        patch("open_hoops.analyzer.OpenHoop", return_value=mock_oh),
    ):
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    player_stats = (
        db_session.query(GamePlayerStats).filter(GamePlayerStats.game_id == game.id).all()
    )
    assert len(player_stats) == 1
    ps = player_stats[0]
    assert ps.player_id == player.id
    assert ps.jersey_number == 23
    assert ps.distance_covered_m == 1500.0
    assert ps.shot_attempts == 5
    assert ps.shot_makes == 3
    assert ps.passes_made == 4
    assert ps.passes_received == 6
    assert ps.possession_frames == 200


def test_analyze_writes_events(db_session, game_setup):
    from open_hoops.models import BBox
    from open_hoops.models import GameEvent as OHGameEvent

    events = [
        OHGameEvent(
            type="shot",
            frame=100,
            timestamp_sec=3.33,
            team_id="team_a",
            player_id=23,
            bbox=BBox(x1=10, y1=20, x2=50, y2=80),
        ),
        OHGameEvent(
            type="pass",
            frame=200,
            timestamp_sec=6.66,
            team_id="team_b",
            player_id=None,
            bbox=None,
        ),
    ]
    game, home, away, player = game_setup
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats(events=events)

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)),
        patch("open_hoops.analyzer.OpenHoop", return_value=mock_oh),
    ):
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    db_events = (
        db_session.query(GameEvent)
        .filter(GameEvent.game_id == game.id)
        .order_by(GameEvent.frame)
        .all()
    )
    assert len(db_events) == 2

    ev1 = db_events[0]
    assert ev1.type == "shot"
    assert ev1.frame == 100
    assert ev1.team_id == home.id
    assert ev1.player_id == player.id
    assert ev1.source == EventSource.analysis
    assert ev1.bbox_x1 == 10
    assert ev1.bbox_y1 == 20
    assert ev1.bbox_x2 == 50
    assert ev1.bbox_y2 == 80

    ev2 = db_events[1]
    assert ev2.type == "pass"
    assert ev2.team_id == away.id
    assert ev2.player_id is None
    assert ev2.bbox_x1 is None


def test_analyze_game_not_found(db_session):
    """analyze_game returns early if game UID doesn't exist."""
    with patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)):
        from worker.tasks import analyze_game

        analyze_game("nonexistent_uid_1234567890ab")


def test_analyze_sets_processing_status(db_session, game_setup):
    """Game status transitions to processing before analysis starts."""
    game, _home, _away, _player = game_setup

    statuses_seen = []

    def capture_status(*args, **kwargs):
        db_session.refresh(game)
        statuses_seen.append(game.status)
        return make_stats()

    mock_oh = MagicMock()
    mock_oh.extract_stats.side_effect = capture_status

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)),
        patch("open_hoops.analyzer.OpenHoop", return_value=mock_oh),
    ):
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    assert GameStatus.processing in statuses_seen


def test_analyze_failure_sets_failed_status(db_session, game_setup):
    """If analysis raises, game status becomes failed."""
    game, _home, _away, _player = game_setup
    mock_oh = MagicMock()
    mock_oh.extract_stats.side_effect = RuntimeError("Model crash")

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)),
        patch("open_hoops.analyzer.OpenHoop", return_value=mock_oh),
    ):
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    db_session.refresh(game)
    assert game.status == GameStatus.failed
