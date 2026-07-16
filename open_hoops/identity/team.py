from __future__ import annotations
import cv2
import numpy as np
from sklearn.cluster import KMeans


def _torso_crop(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    h = y2 - y1
    # use middle third vertically (torso), full width
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


def _dominant_bgr(crop: np.ndarray) -> tuple[int, int, int]:
    pixels = crop.reshape(-1, 3).astype(np.float32)
    if len(pixels) < 4:
        return (int(pixels[0, 0]), int(pixels[0, 1]), int(pixels[0, 2]))
    km = KMeans(n_clusters=1, n_init=1, random_state=0).fit(pixels)
    b, g, r = km.cluster_centers_[0].astype(int)
    return int(r), int(g), int(b)


class TeamClassifier:
    def __init__(self) -> None:
        self._kmeans: KMeans | None = None
        self.team_colors: dict[str, str] = {}

    def fit(
        self,
        frames: list[np.ndarray],
        player_bboxes: list[list[tuple[int, int, int, int]]],
    ) -> None:
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

        # assign colors from first crop of each cluster
        for label, team_id in enumerate(("team_a", "team_b")):
            idx = np.where(self._kmeans.labels_ == label)[0]
            if len(idx) == 0:
                self.team_colors[team_id] = "#000000"
                continue
            r, g, b = _dominant_bgr(crops_for_color[idx[0]])
            self.team_colors[team_id] = f"#{r:02x}{g:02x}{b:02x}"

    def assign(
        self, frame: np.ndarray, bbox: tuple[int, int, int, int]
    ) -> str:
        if self._kmeans is None:
            return "team_a"
        crop = _torso_crop(frame, bbox)
        if crop.size == 0:
            return "team_a"
        hist = _hsv_histogram(crop).reshape(1, -1)
        label = int(self._kmeans.predict(hist)[0])
        return "team_a" if label == 0 else "team_b"
