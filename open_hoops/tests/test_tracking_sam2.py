from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from open_hoops.tracking.sam2_tracker import SAM2Tracker, TrackedFrame, TrackedPlayer


@patch("open_hoops.tracking.sam2_tracker.build_sam2_camera_predictor")
def test_prompt_first_frame(mock_build):
    mock_predictor = MagicMock()
    mock_build.return_value = mock_predictor

    tracker = SAM2Tracker()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detections = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300], [400, 200, 450, 300]]),
        confidence=np.array([0.9, 0.85]),
        class_id=np.array([3, 3]),
        tracker_id=np.array([1, 2]),
    )
    tracker.prompt_first_frame(frame, detections)

    mock_predictor.load_first_frame.assert_called_once()
    assert mock_predictor.add_new_prompt.call_count == 2


@patch("open_hoops.tracking.sam2_tracker.build_sam2_camera_predictor")
def test_track_frame_returns_detections_with_masks(mock_build):
    mock_predictor = MagicMock()
    mock_build.return_value = mock_predictor

    # Simulate SAM2 output: dict of obj_id -> mask
    mask1 = np.zeros((720, 1280), dtype=bool)
    mask1[200:300, 100:150] = True
    mask2 = np.zeros((720, 1280), dtype=bool)
    mask2[200:300, 400:450] = True
    mock_predictor.track.return_value = ({1: mask1, 2: mask2}, {1: 0.95, 2: 0.9})

    tracker = SAM2Tracker()
    tracker._predictor = mock_predictor
    tracker._prompted = True

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = tracker.track_frame(frame)

    assert isinstance(result, sv.Detections)
    assert len(result) == 2
    assert result.tracker_id is not None
    assert result.mask is not None


def test_tracked_frame_dataclass():
    player = TrackedPlayer(track_id=1, bbox=(100, 200, 150, 300), court_pos=(5.0, 7.0))
    tf = TrackedFrame(players=[player], ball_pos=(10.0, 5.0), frame_idx=42)
    assert tf.players[0].track_id == 1
    assert tf.ball_pos == (10.0, 5.0)
    assert tf.frame_idx == 42
