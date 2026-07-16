import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from open_hoops.analyzer import Analyzer
from open_hoops.models import GameStats
from open_hoops.detector import FrameDetections
from open_hoops.tracker import TrackedFrame


def make_mock_cap(n_frames=10, width=1280, height=720, fps=30.0):
    cap = MagicMock()
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frames = iter([True] * n_frames + [False])
    cap.read.side_effect = lambda: (next(frames), frame)
    cap.get.side_effect = lambda prop: {
        0: fps,        # CAP_PROP_FPS
        7: n_frames,   # CAP_PROP_FRAME_COUNT
    }.get(prop, 0)
    cap.isOpened.return_value = True
    return cap


def test_invalid_video_raises_value_error():
    with patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap
        with pytest.raises(ValueError, match="Cannot open video"):
            Analyzer("nonexistent.mp4").run()


def test_run_returns_game_stats():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=5)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = Analyzer("fake.mp4").run()
        assert isinstance(stats, GameStats)
        assert stats.video_path == "fake.mp4"
