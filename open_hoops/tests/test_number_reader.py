from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from open_hoops.identity.number_reader import NumberReader, NumberValidator


@patch("open_hoops.identity.number_reader.get_model")
def test_read_returns_dict_of_numbers(mock_get_model):
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_model.infer.side_effect = [
        MagicMock(output="23"),
        MagicMock(output="7"),
    ]

    reader = NumberReader()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detections = sv.Detections(
        xyxy=np.array([[100, 200, 130, 240], [400, 200, 430, 240]]),
        confidence=np.array([0.9, 0.85]),
        class_id=np.array([2, 2]),
    )
    results = reader.read(frame, detections)
    assert results == {0: "23", 1: "7"}


def test_validator_locks_after_consecutive_reads():
    validator = NumberValidator(threshold=3)
    assert validator.update(1, "23") is None
    assert validator.update(1, "23") is None
    assert validator.update(1, "23") == 23
    # Stays locked
    assert validator.update(1, "7") == 23


def test_validator_resets_on_inconsistency():
    validator = NumberValidator(threshold=3)
    validator.update(1, "23")
    validator.update(1, "23")
    validator.update(1, "7")  # breaks streak
    validator.update(1, "7")
    validator.update(1, "7")
    assert validator.update(1, "7") == 7


def test_validator_handles_non_numeric():
    validator = NumberValidator(threshold=2)
    assert validator.update(1, "abc") is None
    assert validator.update(1, "") is None
    assert validator.update(1, "23") is None
    assert validator.update(1, "23") == 23
