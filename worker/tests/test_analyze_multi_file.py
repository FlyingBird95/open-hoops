import datetime
from unittest.mock import MagicMock, patch

from open_hoops.service.game.models import Game, GameFile, GameStatus
from open_hoops.service.team.models import Team, generate_uid
from open_hoops.models import GameStats, TeamStats
from open_hoops.models import Video as OHVideo


def make_fake_stats(duration=60.0, fps=30.0, path="uploads/fake.mp4"):
    return GameStats(
        video=OHVideo(path=path),
        duration_seconds=duration,
        fps=fps,
        teams=[
            TeamStats(team_id="home", score=10, possession_pct=50.0, players=[]),
            TeamStats(team_id="away", score=8, possession_pct=50.0, players=[]),
        ],
        events=[],
    )


def test_analyze_merges_multiple_files(db_session, monkeypatch):
    home = Team(uid=generate_uid(), name="H", is_own=True)
    away = Team(uid=generate_uid(), name="A", is_own=False)
    db_session.add_all([home, away])
    db_session.flush()

    game = Game(
        uid=generate_uid(),
        name="Multi",
        date=datetime.date(2026, 8, 5),
        own_team_id=home.id,
        opponent_team_id=away.id,
    )
    db_session.add(game)
    db_session.flush()

    for i in range(2):
        db_session.add(
            GameFile(
                uid=generate_uid(),
                game_id=game.id,
                file_path=f"uploads/part{i}.mp4",
                position=i,
                original_filename=f"part{i}.mp4",
                size_bytes=1000,
            )
        )
    db_session.commit()

    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_fake_stats(duration=60.0)

    # Patch SessionLocal to return the test db_session so analyze_game uses the
    # same in-memory SQLite connection as the test.
    # Wrap db_session so close() is a no-op (analyze_game calls db.close() in finally)
    class _NoCloseSession:
        def __init__(self, s):
            self._s = s

        def __getattr__(self, name):
            return getattr(self._s, name)

        def close(self):
            pass

    with (
        patch("worker.tasks.SessionLocal", return_value=_NoCloseSession(db_session)),
        patch("open_hoops.analyzer.OpenHoop", return_value=mock_oh) as MockOH,
    ):
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    db_session.refresh(game)
    assert game.status == GameStatus.done
    assert game.duration_seconds == 120.0  # 60 + 60
    assert MockOH.call_count == 2
