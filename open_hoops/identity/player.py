"""PlayerIdentifier — jersey number OCR using EasyOCR."""

from __future__ import annotations
import re
from typing import TYPE_CHECKING

import numpy as np
import easyocr

if TYPE_CHECKING:
    from open_hoops.pass_one import TrackProfile


class PlayerIdentifier:
    """Extracts player jersey numbers from frames via OCR.

    Runs OCR every 30 frames per track_id and returns majority vote
    of last 10 readings.
    """

    def __init__(self, valid_numbers: set[int] | None = None) -> None:
        self._reader: easyocr.Reader | None = None
        self._frame_counter: dict[int, int] = {}
        self._history: dict[int, list[int]] = {}
        self._valid_numbers = valid_numbers

    def _get_reader(self) -> easyocr.Reader:
        """Lazy-load EasyOCR reader on first call."""
        if self._reader is None:
            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return self._reader

    def _run_ocr(self, frame: np.ndarray, bbox: tuple[int, int, int, int]) -> int | None:
        """Run OCR on torso region of player crop.

        Args:
            frame: Full frame array
            bbox: Bounding box (x1, y1, x2, y2)

        Returns:
            Extracted jersey number or None
        """
        x1, y1, x2, y2 = bbox
        h = y2 - y1
        # Extract torso region (middle 50% of height)
        t_y1 = y1 + h // 4
        t_y2 = y1 + 3 * h // 4
        crop = frame[t_y1:t_y2, x1:x2]

        if crop.size == 0:
            return None

        try:
            results = self._get_reader().readtext(crop, detail=0, allowlist="0123456789")
        except Exception:
            return None

        for text in results:
            digits = re.sub(r"\D", "", text)
            if digits:
                num = int(digits[:2])
                if self._valid_numbers is None or num in self._valid_numbers:
                    return num

        return None

    def _majority(self, track_id: int) -> int | None:
        """Return majority vote of last 10 readings for track_id.

        Args:
            track_id: Player track ID

        Returns:
            Most common jersey number or None if no history
        """
        history = self._history.get(track_id, [])
        if not history:
            return None

        last = history[-10:]
        counts: dict[int, int] = {}
        for v in last:
            counts[v] = counts.get(v, 0) + 1

        return max(counts, key=lambda k: (counts[k], -k))

    def identify(
        self,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int],
        track_id: int,
    ) -> int | None:
        """Extract player jersey number from frame.

        Args:
            frame: Frame as numpy array
            bbox: Player bounding box (x1, y1, x2, y2)
            track_id: Player track ID

        Returns:
            Jersey number (majority vote) or None
        """
        count = self._frame_counter.get(track_id, 0)

        # Run OCR every 30 frames
        if count % 30 == 0:
            number = self._run_ocr(frame, bbox)
            if number is not None:
                self._history.setdefault(track_id, []).append(number)

        self._frame_counter[track_id] = count + 1
        return self._majority(track_id)


def finalize_jerseys(tracks: dict[int, "TrackProfile"]) -> None:
    """Assign jersey number to each TrackProfile using area-weighted majority vote.

    Mutates profile.jersey in place.
    """
    for profile in tracks.values():
        if not profile.ocr_readings:
            profile.jersey = None
            continue

        # Weighted vote: accumulate area per jersey number
        weighted: dict[int, int] = {}
        for number, area in zip(profile.ocr_readings, profile.bbox_areas):
            weighted[number] = weighted.get(number, 0) + area

        profile.jersey = max(weighted, key=weighted.get)
