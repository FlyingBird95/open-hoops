from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from open_hoops.detection.rfdetr import (
    BALL_CLASS_ID,
    BALL_IN_BASKET_CLASS_ID,
    NUMBER_CLASS_ID,
    PLAYER_CLASS_IDS,
    PLAYER_IN_POSSESSION_CLASS_ID,
    PLAYER_JUMP_SHOT_CLASS_ID,
    PLAYER_LAYUP_DUNK_CLASS_ID,
    RFDETRDetector,
)


def _mock_inference_result():
    """Create a mock inference result mimicking Roboflow API response."""
    mock_result = MagicMock()
    mock_result.xyxy = np.array([[100, 200, 150, 300], [400, 200, 450, 300]])
    mock_result.confidence = np.array([0.9, 0.85])
    mock_result.class_id = np.array([3, 4])
    mock_result.data = {}
    return mock_result


@patch("open_hoops.detection.rfdetr.get_model")
def test_detect_returns_supervision_detections(mock_get_model):
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_model.infer.return_value = [_mock_inference_result()]

    with patch("supervision.Detections.from_inference") as mock_from_inf:
        mock_from_inf.return_value = sv.Detections(
            xyxy=np.array([[100, 200, 150, 300], [400, 200, 450, 300]]),
            confidence=np.array([0.9, 0.85]),
            class_id=np.array([3, 4]),
        )
        detector = RFDETRDetector()
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = detector.detect(frame)

    assert isinstance(result, sv.Detections)
    assert len(result) == 2


@patch("open_hoops.detection.rfdetr.get_model")
def test_filter_players(mock_get_model):
    mock_get_model.return_value = MagicMock()

    detector = RFDETRDetector()
    detections = sv.Detections(
        xyxy=np.array([[0, 0, 1, 1]] * 4),
        confidence=np.array([0.9, 0.9, 0.9, 0.9]),
        class_id=np.array([3, 4, 5, 8]),  # player, possession, jump-shot, referee
    )
    players = detector.filter_players(detections)
    assert len(players) == 3  # referee excluded


@patch("open_hoops.detection.rfdetr.get_model")
def test_filter_numbers(mock_get_model):
    mock_get_model.return_value = MagicMock()

    detector = RFDETRDetector()
    detections = sv.Detections(
        xyxy=np.array([[0, 0, 1, 1]] * 3),
        confidence=np.array([0.9, 0.9, 0.9]),
        class_id=np.array([2, 3, 4]),  # number, player, possession
    )
    numbers = detector.filter_numbers(detections)
    assert len(numbers) == 1


def test_class_id_constants():
    assert BALL_CLASS_ID == 0
    assert BALL_IN_BASKET_CLASS_ID == 1
    assert NUMBER_CLASS_ID == 2
    assert 3 in PLAYER_CLASS_IDS
    assert 4 in PLAYER_CLASS_IDS  # player-in-possession
    assert 5 in PLAYER_CLASS_IDS  # player-jump-shot
    assert 6 in PLAYER_CLASS_IDS  # player-layup-dunk
    assert 7 in PLAYER_CLASS_IDS  # player-shot-block
    assert PLAYER_IN_POSSESSION_CLASS_ID == 4
    assert PLAYER_JUMP_SHOT_CLASS_ID == 5
    assert PLAYER_LAYUP_DUNK_CLASS_ID == 6
