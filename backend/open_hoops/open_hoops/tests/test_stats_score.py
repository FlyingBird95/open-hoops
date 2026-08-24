from open_hoops.service.analysis.models import AnalyzedEvent
from open_hoops.stats.score import ScoreTracker


def make_make_event(team_id):
    return AnalyzedEvent(type="make", frame=1, timestamp_sec=0.033, team_id=team_id)


def make_shot_event(team_id):
    return AnalyzedEvent(type="shot", frame=1, timestamp_sec=0.033, team_id=team_id)


def test_score_increments_on_make():
    tracker = ScoreTracker()
    tracker.update([make_make_event("team_a")])
    assert tracker.scores["team_a"] == 2
    assert tracker.scores["team_b"] == 0


def test_score_ignores_shot_events():
    tracker = ScoreTracker()
    tracker.update([make_shot_event("team_a")])
    assert tracker.scores["team_a"] == 0


def test_score_accumulates_multiple_makes():
    tracker = ScoreTracker()
    tracker.update([make_make_event("team_b")])
    tracker.update([make_make_event("team_b")])
    assert tracker.scores["team_b"] == 4
