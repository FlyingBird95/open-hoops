from open_hoops.stats.movement import MovementTracker
from open_hoops.tracker import TrackedFrame, TrackedPlayer


def make_tf(players, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players
    return tf


def test_distance_accumulates():
    tracker = MovementTracker()
    p1 = TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(0.0, 0.0))
    p2 = TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(3.0, 4.0))  # dist=5
    tracker.update(make_tf([p1], 0))
    tracker.update(make_tf([p2], 1))
    assert abs(tracker.get_distance(1) - 5.0) < 0.001


def test_positions_recorded():
    tracker = MovementTracker()
    p = TrackedPlayer(track_id=2, bbox=(0, 0, 1, 1), court_pos=(1.0, 2.0))
    tracker.update(make_tf([p], 0))
    positions = tracker.get_positions(2)
    assert positions == [(1.0, 2.0)]


def test_unknown_track_id_returns_zero():
    tracker = MovementTracker()
    assert tracker.get_distance(999) == 0.0
    assert tracker.get_positions(999) == []
