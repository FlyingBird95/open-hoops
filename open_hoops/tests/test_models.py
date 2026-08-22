import json

from open_hoops.models import AnalyzedEvent, AnalysisResult, AnalyzedPlayerStats, Video


def test_video_model():
    v = Video(path="game.mp4")
    assert v.path == "game.mp4"
    assert json.dumps(v.model_dump())


def test_gamestats_uses_video_model():
    stats = AnalysisResult(
        video=Video(path="game.mp4"),
        duration_seconds=60.0,
        fps=30.0,
        teams=[],
        events=[],
    )
    dumped = stats.model_dump()
    assert json.dumps(dumped)
    assert dumped["video"]["path"] == "game.mp4"


def test_player_stats_defaults():
    p = AnalyzedPlayerStats(player_id=None, team_id="team_a")
    assert p.shot_attempts == 0
    assert p.distance_covered_m == 0.0
    assert p.positions == []


def test_game_event_types():
    for t in ("shot", "make", "miss", "pass", "possession_change"):
        e = AnalyzedEvent(type=t, frame=1, timestamp_sec=0.033)
        assert e.type == t
