import numpy as np
from unittest.mock import patch, MagicMock
from open_hoops.pass_one import TrackProfile, PassOneResult, run_pass_one


def test_track_profile_defaults():
    tp = TrackProfile(track_id=1)
    assert tp.track_id == 1
    assert tp.crops == []
    assert tp.histograms == []
    assert tp.ocr_readings == []
    assert tp.bbox_areas == []
    assert tp.team is None
    assert tp.jersey is None


def test_pass_one_result_structure():
    tp = TrackProfile(track_id=5)
    result = PassOneResult(
        tracks={5: tp},
        ball_positions=[None, (1.0, 2.0), None],
        frames=[],
        frame_count=3,
        fps=30.0,
    )
    assert result.frame_count == 3
    assert result.tracks[5].track_id == 5
    assert result.ball_positions[1] == (1.0, 2.0)


@patch("open_hoops.pass_one.cv2.VideoCapture")
@patch("open_hoops.pass_one.Detector")
def test_run_pass_one_collects_tracks(mock_detector_cls, mock_cap_cls):
    # Mock video: 5 frames, 1 player track_id=1, ball in frame 0 and 2
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.return_value = 30.0
    frames = [np.zeros((720, 1280, 3), dtype=np.uint8) for _ in range(5)]
    mock_cap.read.side_effect = [(True, f) for f in frames] + [(False, None)]
    mock_cap_cls.return_value = mock_cap

    from open_hoops.detector import Detection, FrameDetections

    player_det = Detection(bbox=(100, 100, 200, 300), conf=0.9, class_name="player", track_id=1)
    ball_det = Detection(bbox=(400, 400, 420, 420), conf=0.5, class_name="ball")
    fd_with_ball = FrameDetections(players=[player_det], ball=ball_det)
    fd_no_ball = FrameDetections(players=[player_det], ball=None)

    mock_detector = MagicMock()
    mock_detector.detect.side_effect = [
        fd_with_ball,
        fd_no_ball,
        fd_with_ball,
        fd_no_ball,
        fd_no_ball,
    ]
    mock_detector_cls.return_value = mock_detector

    result = run_pass_one(
        video_path="fake.mp4",
        model_path="yolo11x.pt",
        src_pts=np.array([[0, 0], [1280, 0], [1280, 720], [0, 720]], dtype=np.float32),
        dst_pts=np.array([[0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]], dtype=np.float32),
        valid_numbers=None,
    )

    assert result.frame_count == 5
    assert result.fps == 30.0
    assert 1 in result.tracks
    assert len(result.ball_positions) == 5
    # Ball present in frame 0 and 2
    assert result.ball_positions[0] is not None
    assert result.ball_positions[1] is None
    assert result.ball_positions[2] is not None
