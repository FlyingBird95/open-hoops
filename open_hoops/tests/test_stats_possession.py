from open_hoops.tracker import TrackedFrame, TrackedPlayer
from open_hoops.stats.possession import PossessionTracker


def make_tf(players, ball_pos, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players
    tf.ball_pos = ball_pos
    return tf


def test_possession_assigned_to_nearest_player():
    tracker = PossessionTracker()
    players = [
        TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(5.0, 5.0)),
        TrackedPlayer(track_id=2, bbox=(0, 0, 1, 1), court_pos=(20.0, 10.0)),
    ]
    tf = make_tf(players, ball_pos=(5.1, 5.1))
    tracker.update(tf, {1: "team_a", 2: "team_b"}, frame_idx=0, fps=30.0)
    assert tracker._current_owner == 1


def test_possession_change_fires_event():
    tracker = PossessionTracker()
    p1 = TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0, 0, 1, 1), court_pos=(20.0, 10.0))
    tracker.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_b"}, 0, 30.0)
    events = tracker.update(make_tf([p1, p2], (19.9, 10.0)), {1: "team_a", 2: "team_b"}, 1, 30.0)
    assert any(e.type == "possession_change" for e in events)


def test_finalize_sums_to_one():
    tracker = PossessionTracker()
    p1 = TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0, 0, 1, 1), court_pos=(20.0, 10.0))
    for i in range(10):
        tracker.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_b"}, i, 30.0)
    pct = tracker.finalize(10)
    assert abs(pct["team_a"] + pct["team_b"] - 1.0) < 0.01


def test_no_ball_no_event():
    tracker = PossessionTracker()
    tf = make_tf([], ball_pos=None)
    events = tracker.update(tf, {}, 0, 30.0)
    assert events == []
