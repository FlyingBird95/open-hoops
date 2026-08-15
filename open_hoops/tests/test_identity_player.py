from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from open_hoops.identity.player import PlayerIdentifier, finalize_jerseys
from open_hoops.pass_one import TrackProfile


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


def test_finalize_jerseys_majority_vote():
    profile = TrackProfile(
        track_id=1,
        ocr_readings=[23, 23, 5, 23, 5],
        bbox_areas=[1000, 1200, 500, 1100, 600],
    )
    tracks = {1: profile}
    finalize_jerseys(tracks)
    assert profile.jersey == 23


def test_finalize_jerseys_weighted_by_area():
    # Same count but larger bbox should win
    profile = TrackProfile(
        track_id=1,
        ocr_readings=[23, 5],
        bbox_areas=[2000, 500],
    )
    tracks = {1: profile}
    finalize_jerseys(tracks)
    assert profile.jersey == 23


def test_finalize_jerseys_no_readings():
    profile = TrackProfile(track_id=1, ocr_readings=[], bbox_areas=[])
    tracks = {1: profile}
    finalize_jerseys(tracks)
    assert profile.jersey is None


def test_finalize_jerseys_multiple_tracks():
    tracks = {
        1: TrackProfile(track_id=1, ocr_readings=[10, 10, 7], bbox_areas=[1000, 1000, 800]),
        2: TrackProfile(track_id=2, ocr_readings=[5, 5], bbox_areas=[900, 900]),
    }
    finalize_jerseys(tracks)
    assert tracks[1].jersey == 10
    assert tracks[2].jersey == 5
