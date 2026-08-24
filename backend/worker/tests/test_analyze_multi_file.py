from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from open_hoops.service.analysis.models import AnalysisResult, AnalyzedTeamStats, Video
from open_hoops.service.game.models import Game, GameStatus
from sqlalchemy.orm import Session
from testhelpers.factories import GameFileFactory
from worker.tasks import analyze_game


def make_fake_stats(duration=60.0, fps=30.0, path="uploads/fake.mp4"):
    return AnalysisResult(
        video=Video(path=path),
        duration_seconds=duration,
        fps=fps,
        teams=[
            AnalyzedTeamStats(team_id="home", score=10, possession_pct=50.0, players=[]),
            AnalyzedTeamStats(team_id="away", score=8, possession_pct=50.0, players=[]),
        ],
        events=[],
    )


class _FakeDatabase:
    def __init__(self, session):
        self._session = session

    @contextmanager
    def use_scoped_session(self):
        yield self._session


def test_analyze_merges_multiple_files(db: Session, game: Game):
    GameFileFactory(game=game, file_path="uploads/part0.mp4", position=0)
    GameFileFactory(game=game, file_path="uploads/part1.mp4", position=1)

    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_fake_stats(duration=60.0)

    with (
        patch("worker.tasks.database", _FakeDatabase(db)),
        patch("worker.tasks.OpenHoop", return_value=mock_oh) as MockOH,
    ):
        analyze_game(game.uid)

    db.refresh(game)
    assert game.status == GameStatus.done
    assert game.duration_seconds == 120.0
    assert MockOH.call_count == 2
