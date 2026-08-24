"""Tests for worker.tasks.analyze_game — single-file, error handling, stats/events persistence."""

from unittest.mock import MagicMock, patch

import pytest
from open_hoops.service.analysis.models import (
    AnalysisResult,
    AnalyzedEvent,
    AnalyzedPlayerStats,
    AnalyzedTeamStats,
    BBox,
    Video,
)
from open_hoops.service.event.models import EventSource, GameEvent
from open_hoops.service.game.models import Game, GameStatus
from open_hoops.service.player.models import Player
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats
from sqlalchemy.orm import Session
from worker.tasks import analyze_game

from testhelpers.lazy import LazyFixtureList


def make_stats(
    duration=60.0,
    fps=30.0,
    home_score=10,
    away_score=8,
    events=None,
    players=None,
):
    home_players = players or [
        AnalyzedPlayerStats(
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
    return AnalysisResult(
        video=Video(path="uploads/fake.mp4"),
        duration_seconds=duration,
        fps=fps,
        teams=[
            AnalyzedTeamStats(
                team_id="team_a", score=home_score, possession_pct=55.0, players=home_players
            ),
            AnalyzedTeamStats(team_id="team_b", score=away_score, possession_pct=45.0, players=[]),
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


@pytest.mark.parametrize("game__files", [LazyFixtureList("game_file")])
def test_analyze_single_file(db: Session, game: Game, player: Player):
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats(duration=90.0, fps=30.0)

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db)),
        patch("worker.tasks.OpenHoop", return_value=mock_oh),
    ):
        analyze_game(game.uid)

    db.refresh(game)
    assert game.status == GameStatus.done
    assert game.duration_seconds == 90.0
    assert game.fps == 30.0
    mock_oh.extract_stats.assert_called_once()


@pytest.mark.parametrize("game__files", [LazyFixtureList("game_file")])
def test_analyze_writes_team_stats(db: Session, game: Game, player: Player):
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats(home_score=25, away_score=20)

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db)),
        patch("worker.tasks.OpenHoop", return_value=mock_oh),
    ):
        analyze_game(game.uid)

    team_stats = db.query(GameTeamStats).filter(GameTeamStats.game_id == game.id).all()
    assert len(team_stats) == 2

    home_stats = next(ts for ts in team_stats if ts.team_id == game.own_team.id)
    away_stats = next(ts for ts in team_stats if ts.team_id == game.opponent_team.id)
    assert home_stats.score == 25
    assert home_stats.possession_pct == 55.0
    assert away_stats.score == 20
    assert away_stats.possession_pct == 45.0


@pytest.mark.parametrize("game__files", [LazyFixtureList("game_file")])
def test_analyze_writes_player_stats(db: Session, game: Game, player: Player):
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats()

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db)),
        patch("worker.tasks.OpenHoop", return_value=mock_oh),
    ):
        analyze_game(game.uid)

    player_stats = db.query(GamePlayerStats).filter(GamePlayerStats.game_id == game.id).all()
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


@pytest.mark.parametrize("game__files", [LazyFixtureList("game_file")])
def test_analyze_writes_events(db: Session, game: Game, player: Player):
    events = [
        AnalyzedEvent(
            type="shot",
            frame=100,
            timestamp_sec=3.33,
            team_id="team_a",
            player_id=23,
            bbox=BBox(x1=10, y1=20, x2=50, y2=80),
        ),
        AnalyzedEvent(
            type="pass",
            frame=200,
            timestamp_sec=6.66,
            team_id="team_b",
            player_id=None,
            bbox=None,
        ),
    ]
    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_stats(events=events)

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db)),
        patch("worker.tasks.OpenHoop", return_value=mock_oh),
    ):
        analyze_game(game.uid)

    db_events = (
        db.query(GameEvent).filter(GameEvent.game_id == game.id).order_by(GameEvent.frame).all()
    )
    assert len(db_events) == 2

    ev1 = db_events[0]
    assert ev1.type == "shot"
    assert ev1.frame == 100
    assert ev1.team_id == game.own_team.id
    assert ev1.player_id == player.id
    assert ev1.source == EventSource.analysis
    assert ev1.bbox_x1 == 10
    assert ev1.bbox_y1 == 20
    assert ev1.bbox_x2 == 50
    assert ev1.bbox_y2 == 80

    ev2 = db_events[1]
    assert ev2.type == "pass"
    assert ev2.team_id == game.opponent_team.id
    assert ev2.player_id is None
    assert ev2.bbox_x1 is None


def test_analyze_game_not_found(db: Session):
    with patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db)):
        analyze_game("nonexistent_uid_1234567890ab")


@pytest.mark.parametrize("game__files", [LazyFixtureList("game_file")])
def test_analyze_sets_processing_status(db: Session, game: Game, player: Player):
    statuses_seen = []

    def capture_status(*args, **kwargs):
        db.refresh(game)
        statuses_seen.append(game.status)
        return make_stats()

    mock_oh = MagicMock()
    mock_oh.extract_stats.side_effect = capture_status

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db)),
        patch("worker.tasks.OpenHoop", return_value=mock_oh),
    ):
        analyze_game(game.uid)

    assert GameStatus.processing in statuses_seen


@pytest.mark.parametrize("game__files", [LazyFixtureList("game_file")])
def test_analyze_failure_sets_failed_status(db: Session, game: Game, player: Player):
    mock_oh = MagicMock()
    mock_oh.extract_stats.side_effect = RuntimeError("Model crash")

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db)),
        patch("worker.tasks.OpenHoop", return_value=mock_oh),
    ):
        analyze_game(game.uid)

    db.refresh(game)
    assert game.status == GameStatus.failed
