import json
from open_hoops.models import GameStats, TeamStats, PlayerStats, GameEvent, Point

def test_gamestats_json_roundtrip():
    stats = GameStats(
        video_path="game.mp4",
        duration_seconds=60.0,
        fps=30.0,
        teams=[],
        events=[],
    )
    dumped = stats.model_dump()
    assert json.dumps(dumped)  # must be JSON-serializable
    assert dumped["video_path"] == "game.mp4"

def test_player_stats_defaults():
    p = PlayerStats(player_id=None, team_id="team_a")
    assert p.shot_attempts == 0
    assert p.distance_covered_m == 0.0
    assert p.positions == []

def test_game_event_types():
    for t in ("shot", "make", "miss", "pass", "possession_change"):
        e = GameEvent(type=t, frame=1, timestamp_sec=0.033)
        assert e.type == t
