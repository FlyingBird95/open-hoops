from open_hoops.stats.shots import ShotDetector

from .conftest import make_tf

HOOPS = [(0.5, 7.62), (28.15, 7.62)]


def test_shot_attempt_detected_when_ball_enters_hoop_region():
    det = ShotDetector(hoop_radius_m=0.45)
    tf_far = make_tf(ball_pos=(14.0, 7.62), hoops=HOOPS, frame_idx=0)
    tf_near = make_tf(ball_pos=(0.6, 7.62), hoops=HOOPS, frame_idx=1)
    det.update(tf_far, {}, None, 0, 30.0)
    events = det.update(tf_near, {}, 1, 1, 30.0)
    assert any(e.type == "shot" for e in events)


def test_make_when_ball_crosses_hoop_center():
    det = ShotDetector(hoop_radius_m=0.45)
    tf_approach = make_tf(ball_pos=(0.6, 7.62), hoops=HOOPS, frame_idx=0)
    tf_center = make_tf(ball_pos=(0.5, 7.62), hoops=HOOPS, frame_idx=1)
    det.update(tf_approach, {}, None, 0, 30.0)
    events = det.update(tf_center, {}, None, 1, 30.0)
    assert any(e.type in ("make", "shot") for e in events)


def test_no_events_when_ball_far_from_hoop():
    det = ShotDetector(hoop_radius_m=0.45)
    tf = make_tf(ball_pos=(14.0, 7.62), hoops=HOOPS)
    events = det.update(tf, {}, None, 0, 30.0)
    assert events == []
