from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv
import torch

from open_hoops.tracking.sam2_tracker import SAM2Tracker, TrackedFrame, TrackedPlayer


@patch("open_hoops.tracking.sam2_tracker.build_sam2_video_predictor")
def test_add_objects_prompts_predictor(mock_build):
    mock_predictor = MagicMock()
    mock_build.return_value = mock_predictor

    tracker = SAM2Tracker()
    state = {"obj_ids": []}
    mock_predictor.init_state.return_value = state

    detections = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300], [400, 200, 450, 300]]),
        confidence=np.array([0.9, 0.85]),
        class_id=np.array([3, 3]),
        tracker_id=np.array([1, 2]),
    )
    tracker.add_objects(state, frame_idx=0, detections=detections)

    assert mock_predictor.add_new_points_or_box.call_count == 2


@patch("open_hoops.tracking.sam2_tracker.build_sam2_video_predictor")
def test_propagate_returns_detections_per_frame(mock_build):
    mock_predictor = MagicMock()
    mock_build.return_value = mock_predictor

    mask1 = torch.zeros((1, 1, 720, 1280))
    mask1[0, 0, 200:300, 100:150] = 1.0
    mask2 = torch.zeros((1, 1, 720, 1280))
    mask2[0, 0, 200:300, 400:450] = 1.0

    masks_frame0 = torch.cat([mask1, mask2], dim=0)

    mock_predictor.propagate_in_video.return_value = iter([(0, [1, 2], masks_frame0)])

    tracker = SAM2Tracker()
    state = {}
    results = tracker.propagate(state)

    assert 0 in results
    assert isinstance(results[0], sv.Detections)
    assert len(results[0]) == 2
    assert results[0].tracker_id is not None
    assert results[0].mask is not None


def test_tracked_frame_dataclass():
    player = TrackedPlayer(track_id=1, bbox=(100, 200, 150, 300), court_pos=(5.0, 7.0))
    tf = TrackedFrame(players=[player], ball_pos=(10.0, 5.0), frame_idx=42)
    assert tf.players[0].track_id == 1
    assert tf.ball_pos == (10.0, 5.0)
    assert tf.frame_idx == 42
