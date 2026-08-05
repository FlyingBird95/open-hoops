import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from open_hoops.detector import Detector, FrameDetections


def make_mock_result(boxes_data):
    """boxes_data: list of (x1,y1,x2,y2, conf, cls_id, track_id|None)"""
    mock_result = MagicMock()
    mock_boxes = MagicMock()
    mock_boxes.xyxy.cpu().numpy.return_value = np.array(
        [[b[0], b[1], b[2], b[3]] for b in boxes_data], dtype=float
    )
    mock_boxes.conf.cpu().numpy.return_value = np.array([b[4] for b in boxes_data], dtype=float)
    mock_boxes.cls.cpu().numpy.return_value = np.array([b[5] for b in boxes_data], dtype=float)
    ids = [b[6] for b in boxes_data]
    if any(i is not None for i in ids):
        mock_boxes.id.cpu().numpy.return_value = np.array(
            [i if i is not None else -1 for i in ids], dtype=float
        )
    else:
        mock_boxes.id = None
    mock_result.boxes = mock_boxes
    mock_result.names = {0: "player", 1: "ball", 2: "hoop"}
    return [mock_result]


@patch("open_hoops.detector.YOLO")
def test_detect_returns_frame_detections(mock_yolo_cls):
    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model
    mock_model.track.return_value = make_mock_result(
        [
            (100, 200, 150, 300, 0.9, 0, 1),
            (400, 200, 450, 300, 0.85, 0, 2),
            (200, 250, 220, 270, 0.8, 1, None),
            (50, 350, 100, 380, 0.95, 2, None),
        ]
    )

    detector = Detector("yolo26n.pt")
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = detector.detect(frame)

    assert isinstance(result, FrameDetections)
    assert len(result.players) == 2
    assert result.ball is not None
    assert len(result.hoops) == 1


@patch("open_hoops.detector.YOLO")
def test_missing_model_raises(mock_yolo_cls):
    mock_yolo_cls.side_effect = FileNotFoundError("Model not found")
    with pytest.raises(FileNotFoundError):
        Detector("nonexistent.pt")
