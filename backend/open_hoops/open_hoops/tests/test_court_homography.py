from unittest.mock import MagicMock, patch

import numpy as np

from open_hoops.court.keypoint_homography import CourtMapper


@patch("open_hoops.court.keypoint_homography.get_model")
def test_detect_keypoints_returns_array(mock_get_model):
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model

    mock_result = MagicMock()
    mock_result.keypoints = MagicMock()
    mock_result.keypoints.xy = np.array([[[100.0, 200.0], [300.0, 400.0], [500.0, 600.0]]])
    mock_result.keypoints.confidence = np.array([[0.9, 0.6, 0.3]])
    mock_model.infer.return_value = [mock_result]

    mapper = CourtMapper(anchor_confidence=0.5)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    keypoints = mapper.detect_keypoints(frame)

    # Only keypoints above anchor_confidence (0.5) returned
    assert keypoints.shape[0] == 2  # 0.9 and 0.6, not 0.3


def test_pixel_to_court_with_known_homography():
    mapper = CourtMapper.__new__(CourtMapper)
    # Identity-like homography for simple test
    mapper._view_transformer = MagicMock()
    mapper._view_transformer.transform_points.return_value = np.array([[14.0, 7.5]])

    points = np.array([[640, 360]])
    result = mapper.pixel_to_court(points)
    assert result.shape == (1, 2)
    assert result[0, 0] == 14.0
