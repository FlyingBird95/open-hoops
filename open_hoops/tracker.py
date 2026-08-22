from dataclasses import dataclass, field

import cv2
import numpy as np

from open_hoops.detector import FrameDetections


@dataclass
class TrackedPlayer:
    track_id: int
    bbox: tuple[int, int, int, int]
    court_pos: tuple[float, float]


@dataclass
class TrackedFrame:
    players: list[TrackedPlayer] = field(default_factory=list)
    ball_pos: tuple[float, float] | None = None
    hoops: list[tuple[float, float]] = field(default_factory=list)
    frame_idx: int = 0


def compute_homography(src_pts: np.ndarray, dst_pts: np.ndarray) -> np.ndarray:
    H, _ = cv2.findHomography(src_pts, dst_pts)
    return H


def _pixel_to_court(px: float, py: float, H: np.ndarray) -> tuple[float, float]:
    pt = np.array([[[px, py]]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(pt, H)
    x, y = transformed[0][0]
    return float(x), float(y)


def _bbox_center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


class Tracker:
    def __init__(self, homography_matrix: np.ndarray) -> None:
        self._H = homography_matrix

    def update(self, fd: FrameDetections, frame_idx: int) -> TrackedFrame:
        tf = TrackedFrame(frame_idx=frame_idx)

        for p in fd.players:
            cx, cy = _bbox_center(p.bbox)
            court_pos = _pixel_to_court(cx, cy, self._H)
            tf.players.append(
                TrackedPlayer(
                    track_id=p.track_id if p.track_id is not None else -1,
                    bbox=p.bbox,
                    court_pos=court_pos,
                )
            )

        if fd.ball is not None:
            cx, cy = _bbox_center(fd.ball.bbox)
            tf.ball_pos = _pixel_to_court(cx, cy, self._H)

        for h in fd.hoops:
            cx, cy = _bbox_center(h.bbox)
            tf.hoops.append(_pixel_to_court(cx, cy, self._H))

        return tf
