"""Pass one: collect raw appearance data for each tracked player across all frames.

No stats are computed here — this is the data-gathering phase of the two-pass
analysis architecture.
"""

from __future__ import annotations
from dataclasses import dataclass, field

import cv2
import numpy as np

from open_hoops.detector import Detector
from open_hoops.tracker import Tracker, compute_homography
from open_hoops.identity.team import _torso_crop, _hsv_histogram
from open_hoops.identity.player import PlayerIdentifier
from open_hoops.models import Roster


@dataclass
class TrackProfile:
    track_id: int
    crops: list[np.ndarray] = field(default_factory=list)
    histograms: list[np.ndarray] = field(default_factory=list)
    ocr_readings: list[int] = field(default_factory=list)
    bbox_areas: list[int] = field(default_factory=list)
    frame_indices: list[int] = field(default_factory=list)
    team: str | None = None
    jersey: int | None = None


@dataclass
class PassOneResult:
    tracks: dict[int, TrackProfile]
    ball_positions: list[tuple[float, float] | None]
    frame_count: int
    fps: float


_MAX_CROPS_PER_TRACK = 20
_OCR_INTERVAL = 15
_DEFAULT_FPS = 30.0


def run_pass_one(
    video_path: str,
    model_path: str,
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    roster: Roster | None,
    valid_numbers: set[int] | None,
) -> PassOneResult:
    """Process a video, collecting appearance data for each tracked player.

    Args:
        video_path: Path to the input video file.
        model_path: Path to the YOLO model weights.
        src_pts: Source points for homography (pixel coords of court corners).
        dst_pts: Destination points for homography (real-world court coords).
        roster: Optional roster with team colors for team assignment.
        valid_numbers: Optional set of valid jersey numbers to filter OCR.

    Returns:
        PassOneResult with per-track appearance data and per-frame ball positions.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or _DEFAULT_FPS
    H = compute_homography(src_pts, dst_pts)
    detector = Detector(model_path)
    tracker = Tracker(H)
    player_ident = PlayerIdentifier(valid_numbers=valid_numbers)

    tracks: dict[int, TrackProfile] = {}
    ball_positions: list[tuple[float, float] | None] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        fd = detector.detect(frame)
        tf = tracker.update(fd, frame_idx)

        # Record ball court position (already transformed by homography in Tracker)
        ball_positions.append(tf.ball_pos)

        # Collect per-track appearance data
        for p in fd.players:
            if p.track_id is None:
                continue
            tid = p.track_id
            if tid not in tracks:
                tracks[tid] = TrackProfile(track_id=tid)

            profile = tracks[tid]
            profile.frame_indices.append(frame_idx)

            # Collect torso crop + HSV histogram (up to _MAX_CROPS_PER_TRACK)
            if len(profile.crops) < _MAX_CROPS_PER_TRACK:
                crop = _torso_crop(frame, p.bbox)
                if crop.size > 0:
                    profile.crops.append(crop)
                    profile.histograms.append(_hsv_histogram(crop))

            # Run OCR at _OCR_INTERVAL frame intervals
            if frame_idx % _OCR_INTERVAL == 0:
                number = player_ident._run_ocr(frame, p.bbox)
                if number is not None:
                    profile.ocr_readings.append(number)
                    area = (p.bbox[2] - p.bbox[0]) * (p.bbox[3] - p.bbox[1])
                    profile.bbox_areas.append(area)

        frame_idx += 1

    cap.release()
    return PassOneResult(
        tracks=tracks,
        ball_positions=ball_positions,
        frame_count=frame_idx,
        fps=fps,
    )
