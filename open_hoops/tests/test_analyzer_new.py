from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from open_hoops.service.analysis.models import AnalysisResult, Roster, TeamRoster, Video


@patch("open_hoops.analyzer.sv.VideoInfo")
@patch("open_hoops.analyzer.CourtMapper")
@patch("open_hoops.analyzer.NumberReader")
@patch("open_hoops.analyzer.NumberValidator")
@patch("open_hoops.analyzer.TeamClassifierWrapper")
@patch("open_hoops.analyzer.SAM2Tracker")
@patch("open_hoops.analyzer.RFDETRDetector")
@patch("open_hoops.analyzer.sv.get_video_frames_generator")
def test_extract_stats_returns_analysis_result(
    mock_frames_gen,
    mock_detector_cls,
    mock_tracker_cls,
    mock_team_cls,
    mock_validator_cls,
    mock_reader_cls,
    mock_court_cls,
    mock_video_info_cls,
):
    # Setup: 3 frames of video
    frames = [np.zeros((720, 1280, 3), dtype=np.uint8) for _ in range(3)]
    mock_frames_gen.return_value = iter(frames)

    mock_video_info_cls.from_video_path.return_value.fps = 30.0

    # Mock detector
    mock_detector = MagicMock()
    mock_detector_cls.return_value = mock_detector
    mock_detector.detect.return_value = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300]]),
        confidence=np.array([0.9]),
        class_id=np.array([3]),
    )
    mock_detector.filter_players.return_value = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300]]),
        confidence=np.array([0.9]),
        class_id=np.array([3]),
        tracker_id=np.array([1]),
    )
    mock_detector.filter_numbers.return_value = sv.Detections.empty()
    mock_detector.filter_ball.return_value = sv.Detections.empty()

    # Mock tracker
    mock_tracker = MagicMock()
    mock_tracker_cls.return_value = mock_tracker
    mock_tracker.track_frame.return_value = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300]]),
        confidence=np.array([0.9]),
        class_id=np.array([3]),
        tracker_id=np.array([1]),
        mask=np.zeros((1, 720, 1280), dtype=bool),
    )

    # Mock team classifier
    mock_team = MagicMock()
    mock_team_cls.return_value = mock_team
    mock_team.predict.return_value = 0

    # Mock court mapper
    mock_court = MagicMock()
    mock_court_cls.return_value = mock_court
    mock_court.compute_homography.return_value = True
    mock_court.pixel_to_court.return_value = np.array([[14.0, 7.5]])

    # Mock number reader/validator
    mock_reader = MagicMock()
    mock_reader_cls.return_value = mock_reader
    mock_reader.read.return_value = {}
    mock_validator = MagicMock()
    mock_validator_cls.return_value = mock_validator

    from open_hoops.analyzer import OpenHoop

    roster = Roster(
        home=TeamRoster(color="#FF0000", players=[23]),
        away=TeamRoster(color="#0000FF", players=[7]),
    )
    oh = OpenHoop(Video(path="test.mp4"), roster=roster)
    result = oh.extract_stats()

    assert isinstance(result, AnalysisResult)
    assert result.fps > 0
