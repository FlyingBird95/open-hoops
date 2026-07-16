import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from open_hoops.identity.player import PlayerIdentifier


@pytest.fixture
def player_id_frame():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    return frame


def test_identify_returns_none_on_ocr_failure(player_id_frame):
    ident = PlayerIdentifier()
    with patch("open_hoops.identity.player.easyocr") as mock_ocr:
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []
        mock_ocr.Reader.return_value = mock_reader
        result = ident.identify(player_id_frame, (100, 200, 150, 300), track_id=1)
    assert result is None


def test_identify_majority_vote(player_id_frame):
    ident = PlayerIdentifier()
    with patch.object(ident, "_run_ocr", return_value=23):
        # Call identify() at frame multiples of 30 to trigger OCR
        for i in range(10):
            frame_num = i * 30
            ident._frame_counter[1] = frame_num
            ident.identify(player_id_frame, (100, 200, 150, 300), track_id=1)
    result = ident._majority(1)
    assert result == 23


def test_identify_skips_frames(player_id_frame):
    ident = PlayerIdentifier()
    called = []
    with patch.object(ident, "_run_ocr", side_effect=lambda f, b: called.append(1) or 5):
        for frame_num in range(90):
            ident.identify(player_id_frame, (100, 200, 150, 300), track_id=1)
    # OCR called only at frames 0, 30, 60 → 3 times
    assert len(called) == 3
