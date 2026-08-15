import numpy as np
import pytest

from open_hoops.detector import Detection, FrameDetections
from open_hoops.tracker import TrackedFrame, Tracker, compute_homography


@pytest.fixture
def identity_homography():
    return np.eye(3, dtype=np.float64)


def make_fd(players=None, ball=None, hoops=None):
    fd = FrameDetections()
    fd.players = players or []
    fd.ball = ball
    fd.hoops = hoops or []
    return fd


def test_tracker_returns_tracked_frame(identity_homography):
    tracker = Tracker(identity_homography)
    player = Detection(bbox=(100, 200, 150, 300), conf=0.9, class_name="player", track_id=1)
    ball = Detection(bbox=(200, 250, 220, 270), conf=0.8, class_name="ball")
    fd = make_fd(players=[player], ball=ball)

    result = tracker.update(fd, frame_idx=0)
    assert isinstance(result, TrackedFrame)
    assert len(result.players) == 1
    assert result.players[0].track_id == 1
    assert result.ball_pos is not None


def test_tracker_no_ball(identity_homography):
    tracker = Tracker(identity_homography)
    fd = make_fd()
    result = tracker.update(fd, frame_idx=5)
    assert result.ball_pos is None
    assert result.players == []


def test_compute_homography_returns_matrix():
    src = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
    dst = np.array([[0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]], dtype=np.float32)
    H = compute_homography(src, dst)
    assert H.shape == (3, 3)
