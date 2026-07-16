import warnings
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from open_hoops.analyzer import OpenHoop
from open_hoops.models import GameStats, Video
from open_hoops.detector import FrameDetections
from open_hoops.tracker import TrackedFrame


def make_mock_cap(n_frames=10, width=1280, height=720, fps=30.0):
    cap = MagicMock()
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    reads = [True] * n_frames + [False]
    call_count = [0]

    def _read():
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(reads):
            return reads[idx], frame
        return False, frame

    cap.read.side_effect = _read
    cap.get.side_effect = lambda prop: {
        0: fps,
        7: n_frames,
    }.get(prop, 0)
    cap.isOpened.return_value = True
    return cap


def test_invalid_video_raises_value_error():
    with patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap
        with pytest.raises(ValueError, match="Cannot open video"):
            OpenHoop(Video("nonexistent.mp4")).extract_stats()


def test_extract_stats_returns_game_stats():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=5)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = OpenHoop(Video("fake.mp4")).extract_stats()
        assert isinstance(stats, GameStats)
        assert stats.video.path == "fake.mp4"


def test_extract_stats_crosses_warmup_boundary():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=35)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = OpenHoop(Video("fake.mp4")).extract_stats()
        assert isinstance(stats, GameStats)
        assert stats.fps == 30.0
        assert abs(stats.duration_seconds - 35 / 30.0) < 0.01


def test_ball_missing_warning_issued():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=160)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            OpenHoop(Video("fake.mp4")).extract_stats()

        msgs = [str(w.message) for w in caught]
        assert any("Ball not detected for 5+" in m for m in msgs), f"No ball warning in: {msgs}"


def test_edit_overlay_returns_video():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.cv2.VideoWriter") as mock_writer_cls,
    ):
        mock_cap = make_mock_cap(n_frames=5)
        mock_cap_cls.return_value = mock_cap
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        from open_hoops.models import GameStats, Video, TeamStats
        fake_stats = GameStats(
            video=Video(path="fake.mp4"),
            duration_seconds=5 / 30.0,
            fps=30.0,
            teams=[
                TeamStats(team_id="team_a", color="#ff0000", score=4),
                TeamStats(team_id="team_b", color="#0000ff", score=2),
            ],
            events=[],
        )

        hoops = OpenHoop(Video("fake.mp4"))
        result = hoops.edit_overlay(fake_stats, "out.mp4")
        assert isinstance(result, Video)
        assert result.path == "out.mp4"


def test_edit_overlay_raises_on_invalid_video():
    with patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap

        from open_hoops.models import GameStats, Video
        fake_stats = GameStats(
            video=Video(path="bad.mp4"),
            duration_seconds=1.0,
            fps=30.0,
        )
        with pytest.raises(ValueError, match="Cannot open video"):
            OpenHoop(Video("bad.mp4")).edit_overlay(fake_stats, "out.mp4")
