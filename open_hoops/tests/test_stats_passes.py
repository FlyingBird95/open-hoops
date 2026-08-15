from open_hoops.stats.passes import PassDetector
from open_hoops.tracker import TrackedFrame, TrackedPlayer


def make_tf(players, ball_pos, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players
    tf.ball_pos = ball_pos
    return tf


def test_pass_detected_on_zone_change():
    det = PassDetector()
    p1 = TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0, 0, 1, 1), court_pos=(20.0, 10.0))

    # ball near p1
    det.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_a"}, 1, 0, 30.0, False)
    # ball moves to p2
    events = det.update(
        make_tf([p1, p2], (19.9, 10.0)), {1: "team_a", 2: "team_a"}, 2, 1, 30.0, False
    )
    assert any(e.type == "pass" for e in events)


def test_no_pass_when_shot_this_frame():
    det = PassDetector()
    p1 = TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0, 0, 1, 1), court_pos=(20.0, 10.0))

    det.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_a"}, 1, 0, 30.0, False)
    events = det.update(
        make_tf([p1, p2], (19.9, 10.0)),
        {1: "team_a", 2: "team_a"},
        2,
        1,
        30.0,
        shot_this_frame=True,
    )
    assert not any(e.type == "pass" for e in events)


def test_no_pass_on_first_frame():
    det = PassDetector()
    p1 = TrackedPlayer(track_id=1, bbox=(0, 0, 1, 1), court_pos=(5.0, 5.0))
    events = det.update(make_tf([p1], (5.1, 5.1)), {1: "team_a"}, 1, 0, 30.0, False)
    assert events == []
