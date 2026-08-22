import numpy as np
import pytest

from open_hoops.tracker import TrackedFrame


def make_tf(players=None, ball_pos=None, hoops=None, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players or []
    if ball_pos is not None:
        tf.ball_pos = ball_pos
    if hoops is not None:
        tf.hoops = hoops
    return tf


@pytest.fixture
def blank_frame():
    return np.zeros((720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def fake_detections():
    return {
        "players": [
            {"track_id": 1, "bbox": [100, 200, 150, 300], "conf": 0.9},
            {"track_id": 2, "bbox": [400, 200, 450, 300], "conf": 0.85},
        ],
        "ball": {"bbox": [200, 250, 220, 270], "conf": 0.8},
        "hoops": [
            {"bbox": [50, 350, 100, 380], "conf": 0.95},
            {"bbox": [1180, 350, 1230, 380], "conf": 0.95},
        ],
    }
