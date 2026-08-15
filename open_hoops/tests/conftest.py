import numpy as np
import pytest


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
