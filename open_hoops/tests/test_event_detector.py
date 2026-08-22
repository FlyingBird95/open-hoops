import numpy as np
import supervision as sv

from open_hoops.stats.event_detector import EventDetector


def _make_detections(class_ids, tracker_ids=None):
    n = len(class_ids)
    return sv.Detections(
        xyxy=np.array([[0, 0, 1, 1]] * n),
        confidence=np.array([0.9] * n),
        class_id=np.array(class_ids),
        tracker_id=np.array(tracker_ids) if tracker_ids else None,
    )


def test_detects_jump_shot_event():
    detector = EventDetector()
    teams = {1: "team_a"}
    detections = _make_detections([5], tracker_ids=[1])  # player-jump-shot
    events = detector.update(detections, teams, frame_idx=10, fps=30.0)
    shot_events = [e for e in events if e.type == "shot"]
    assert len(shot_events) == 1
    assert shot_events[0].team_id == "team_a"


def test_detects_make_from_ball_in_basket():
    detector = EventDetector()
    teams = {1: "team_a"}
    # First: shot attempt
    detector.update(_make_detections([5], tracker_ids=[1]), teams, frame_idx=10, fps=30.0)
    # Then: ball in basket
    events = detector.update(_make_detections([1]), teams, frame_idx=15, fps=30.0)
    make_events = [e for e in events if e.type == "make"]
    assert len(make_events) == 1


def test_detects_possession_from_class():
    detector = EventDetector()
    teams = {1: "team_a", 2: "team_b"}
    # Player 1 has possession
    detector.update(_make_detections([4], tracker_ids=[1]), teams, frame_idx=0, fps=30.0)
    # Player 2 has possession (team change)
    events = detector.update(_make_detections([4], tracker_ids=[2]), teams, frame_idx=5, fps=30.0)
    poss_events = [e for e in events if e.type == "possession_change"]
    assert len(poss_events) == 1
    assert poss_events[0].team_id == "team_b"


def test_no_duplicate_shot_same_sequence():
    detector = EventDetector()
    teams = {1: "team_a"}
    detector.update(_make_detections([5], tracker_ids=[1]), teams, frame_idx=10, fps=30.0)
    # Same shot continuing next frame should not fire again
    events = detector.update(_make_detections([5], tracker_ids=[1]), teams, frame_idx=11, fps=30.0)
    shot_events = [e for e in events if e.type == "shot"]
    assert len(shot_events) == 0
