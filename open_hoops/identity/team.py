from __future__ import annotations
import cv2
import numpy as np
from sklearn.cluster import KMeans

from open_hoops.models import Roster


def _torso_crop(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    h = y2 - y1
    t_y1 = y1 + h // 3
    t_y2 = y1 + 2 * h // 3
    crop = frame[t_y1:t_y2, x1:x2]
    return crop if crop.size > 0 else frame[y1:y2, x1:x2]


def _hsv_histogram(crop: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h_hist = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
    s_hist = cv2.calcHist([hsv], [1], None, [8], [0, 256]).flatten()
    hist = np.concatenate([h_hist, s_hist])
    norm = np.linalg.norm(hist)
    return hist / norm if norm > 0 else hist


def _hex_to_bgr(hex_color: str) -> np.ndarray:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return np.array([b, g, r], dtype=np.float32)


def _dominant_bgr(crop: np.ndarray) -> tuple[int, int, int]:
    pixels = crop.reshape(-1, 3).astype(np.float32)
    if len(pixels) < 4:
        b, g, r = int(pixels[0, 0]), int(pixels[0, 1]), int(pixels[0, 2])
        return r, g, b
    km = KMeans(n_clusters=1, n_init=1, random_state=0).fit(pixels)
    b, g, r = km.cluster_centers_[0].astype(int)
    return int(r), int(g), int(b)


class TeamClassifier:
    def __init__(self, roster: Roster | None = None) -> None:
        self._roster = roster
        self._kmeans: KMeans | None = None
        self.team_colors: dict[str, str] = {}

        if roster:
            self._home_bgr = _hex_to_bgr(roster.home.color)
            self._away_bgr = _hex_to_bgr(roster.away.color)
            self.team_colors = {
                "team_a": roster.home.color,
                "team_b": roster.away.color,
            }

    def fit(
        self,
        frames: list[np.ndarray],
        player_bboxes: list[list[tuple[int, int, int, int]]],
    ) -> None:
        if self._roster:
            return

        histograms = []
        crops_for_color: list[np.ndarray] = []
        for frame, bboxes in zip(frames[:30], player_bboxes[:30]):
            for bbox in bboxes:
                crop = _torso_crop(frame, bbox)
                if crop.size == 0:
                    continue
                histograms.append(_hsv_histogram(crop))
                crops_for_color.append(crop)

        if len(histograms) < 2:
            return

        X = np.array(histograms)
        self._kmeans = KMeans(n_clusters=2, n_init=10, random_state=0).fit(X)

        for label, team_id in enumerate(("team_a", "team_b")):
            idx = np.where(self._kmeans.labels_ == label)[0]
            if len(idx) == 0:
                self.team_colors[team_id] = "#000000"
                continue
            r, g, b = _dominant_bgr(crops_for_color[idx[0]])
            self.team_colors[team_id] = f"#{r:02x}{g:02x}{b:02x}"

    def assign(self, frame: np.ndarray, bbox: tuple[int, int, int, int]) -> str:
        crop = _torso_crop(frame, bbox)
        if crop.size == 0:
            return "team_a"

        if self._roster:
            pixels = crop.reshape(-1, 3).astype(np.float32)
            mean_bgr = pixels.mean(axis=0)
            dist_home = np.linalg.norm(mean_bgr - self._home_bgr)
            dist_away = np.linalg.norm(mean_bgr - self._away_bgr)
            return "team_a" if dist_home <= dist_away else "team_b"

        if self._kmeans is None:
            return "team_a"
        hist = _hsv_histogram(crop).reshape(1, -1)
        label = int(self._kmeans.predict(hist)[0])
        return "team_a" if label == 0 else "team_b"
