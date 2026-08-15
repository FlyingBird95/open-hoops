from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from open_hoops.analyzer import OpenHoop
from open_hoops.models import GameStats, Video
from open_hoops.tracker import TrackedFrame


def _make_pass_one_result(n_frames=10, fps=30.0):
    from open_hoops.pass_one import PassOneResult

    return PassOneResult(
        tracks={},
        ball_positions=[None] * n_frames,
        frames=[TrackedFrame(frame_idx=i) for i in range(n_frames)],
        frame_count=n_frames,
        fps=fps,
    )


@patch("open_hoops.analyzer.run_pass_one")
def test_invalid_video_path_still_works(mock_p1):
    mock_p1.return_value = _make_pass_one_result()
    stats = OpenHoop(Video("nonexistent.mp4")).extract_stats()
    assert isinstance(stats, GameStats)


@patch("open_hoops.analyzer.run_pass_one")
def test_extract_stats_returns_game_stats(mock_p1):
    mock_p1.return_value = _make_pass_one_result(n_frames=5)
    stats = OpenHoop(Video("fake.mp4")).extract_stats()
    assert isinstance(stats, GameStats)
    assert stats.video.path == "fake.mp4"


@patch("open_hoops.analyzer.run_pass_one")
def test_extract_stats_crosses_warmup_boundary(mock_p1):
    mock_p1.return_value = _make_pass_one_result(n_frames=35)
    stats = OpenHoop(Video("fake.mp4")).extract_stats()
    assert isinstance(stats, GameStats)
    assert stats.fps == 30.0
    assert abs(stats.duration_seconds - 35 / 30.0) < 0.01


@patch("open_hoops.analyzer.run_pass_one")
def test_ball_missing_completes(mock_p1):
    mock_p1.return_value = _make_pass_one_result(n_frames=160)
    stats = OpenHoop(Video("fake.mp4")).extract_stats()
    assert isinstance(stats, GameStats)


def test_edit_overlay_returns_video():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.cv2.VideoWriter") as mock_writer_cls,
    ):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0
        mock_cap.read.side_effect = [(True, frame)] * 5 + [(False, None)]
        mock_cap_cls.return_value = mock_cap
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        from open_hoops.models import TeamStats

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

        fake_stats = GameStats(
            video=Video(path="bad.mp4"),
            duration_seconds=1.0,
            fps=30.0,
        )
        with pytest.raises(ValueError, match="Cannot open video"):
            OpenHoop(Video("bad.mp4")).edit_overlay(fake_stats, "out.mp4")


@patch("open_hoops.analyzer.run_pass_one")
def test_extract_stats_uses_assignments(mock_p1):
    from open_hoops.models import Roster, TeamRoster
    from open_hoops.pass_one import PassOneResult, TrackProfile

    profile = TrackProfile(track_id=1)
    profile.team = "team_a"
    profile.jersey = 23
    pass_one_result = PassOneResult(
        tracks={1: profile},
        ball_positions=[(1.0, 2.0)] * 10,
        frames=[TrackedFrame(frame_idx=i) for i in range(10)],
        frame_count=10,
        fps=30.0,
    )
    mock_p1.return_value = pass_one_result

    roster = Roster(
        home=TeamRoster(color="#ff0000", players=[23]),
        away=TeamRoster(color="#0000ff", players=[5]),
    )
    stats = OpenHoop(Video(path="fake.mp4"), roster=roster).extract_stats()

    mock_p1.assert_called_once()
    assert stats.fps == 30.0
