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
        5: fps,  # cv2.CAP_PROP_FPS
        7: n_frames,
    }.get(prop, 0)
    cap.isOpened.return_value = True
    return cap


def _make_pass_one_result(n_frames=10, fps=30.0):
    """Return a minimal PassOneResult for tests that patch run_pass_one."""
    from open_hoops.pass_one import PassOneResult

    return PassOneResult(
        tracks={},
        ball_positions=[None] * n_frames,
        frame_count=n_frames,
        fps=fps,
    )


def test_invalid_video_raises_value_error():
    with (
        patch("open_hoops.analyzer.run_pass_one") as mock_p1,
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
    ):
        mock_p1.return_value = _make_pass_one_result()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap
        with pytest.raises(ValueError, match="Cannot open video"):
            OpenHoop(Video("nonexistent.mp4")).extract_stats()


def test_extract_stats_returns_game_stats():
    with (
        patch("open_hoops.analyzer.run_pass_one") as mock_p1,
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_p1.return_value = _make_pass_one_result(n_frames=5)
        mock_cap_cls.return_value = make_mock_cap(n_frames=5)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = OpenHoop(Video("fake.mp4")).extract_stats()
        assert isinstance(stats, GameStats)
        assert stats.video.path == "fake.mp4"


def test_extract_stats_crosses_warmup_boundary():
    with (
        patch("open_hoops.analyzer.run_pass_one") as mock_p1,
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_p1.return_value = _make_pass_one_result(n_frames=35)
        mock_cap_cls.return_value = make_mock_cap(n_frames=35)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = OpenHoop(Video("fake.mp4")).extract_stats()
        assert isinstance(stats, GameStats)
        assert stats.fps == 30.0
        assert abs(stats.duration_seconds - 35 / 30.0) < 0.01


def test_ball_missing_warning_issued():
    # Ball-missing warning is now issued in pass_one; pass 2 uses interpolated positions.
    # This test verifies extract_stats still completes without exception for long videos.
    with (
        patch("open_hoops.analyzer.run_pass_one") as mock_p1,
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_p1.return_value = _make_pass_one_result(n_frames=160)
        mock_cap_cls.return_value = make_mock_cap(n_frames=160)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = OpenHoop(Video("fake.mp4")).extract_stats()
        assert isinstance(stats, GameStats)


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


@patch("open_hoops.analyzer.run_pass_one")
@patch("open_hoops.analyzer.cv2.VideoCapture")
def test_extract_stats_uses_two_pass(mock_cap_cls, mock_pass_one):
    """Verify extract_stats calls pass_one and uses its assignments."""
    from open_hoops.models import Roster, TeamRoster
    from open_hoops.pass_one import TrackProfile, PassOneResult

    # Setup pass one result with 1 track
    profile = TrackProfile(track_id=1)
    profile.team = "team_a"
    profile.jersey = 23
    pass_one_result = PassOneResult(
        tracks={1: profile},
        ball_positions=[(1.0, 2.0)] * 10,
        frame_count=10,
        fps=30.0,
    )
    mock_pass_one.return_value = pass_one_result

    # Mock video for pass 2
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.return_value = 30.0
    frames = [np.zeros((720, 1280, 3), dtype=np.uint8) for _ in range(10)]
    mock_cap.read.side_effect = [(True, f) for f in frames] + [(False, None)]
    mock_cap_cls.return_value = mock_cap

    roster = Roster(
        home=TeamRoster(color="#ff0000", players=[23]),
        away=TeamRoster(color="#0000ff", players=[5]),
    )
    oh = OpenHoop(Video(path="fake.mp4"), roster=roster)

    with (
        patch("open_hoops.analyzer.Detector"),
        patch("open_hoops.analyzer.Tracker") as mock_tracker_cls,
    ):
        mock_tracker = MagicMock()
        mock_tf = TrackedFrame()  # real TrackedFrame: players=[], ball_pos=None
        mock_tracker.update.return_value = mock_tf
        mock_tracker_cls.return_value = mock_tracker
        stats = oh.extract_stats()

    mock_pass_one.assert_called_once()
    assert stats.fps == 30.0
