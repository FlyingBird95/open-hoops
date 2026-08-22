from typing import TYPE_CHECKING

import cv2
import numpy as np
from sklearn.cluster import KMeans

from open_hoops.models import Roster

if TYPE_CHECKING:
    from open_hoops.pass_one import TrackProfile


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


def assign_teams_from_profiles(
    tracks: dict[int, "TrackProfile"],
    roster: Roster | None,
) -> None:
    """Assign team to each TrackProfile by clustering all histograms.

    Mutates profile.team in place. Uses KMeans on combined histograms
    from all tracks to find 2 clusters, then maps clusters to team_a/team_b.
    If roster is provided, matches clusters to roster colors.
    """
    # Collect all histograms with their track_id
    all_hists: list[tuple[int, np.ndarray]] = []
    for tid, profile in tracks.items():
        for h in profile.histograms:
            all_hists.append((tid, h))

    if len(all_hists) < 2:
        # Can't cluster, assign all to team_a
        for profile in tracks.values():
            profile.team = "team_a"
        return

    X = np.array([h for _, h in all_hists])
    km = KMeans(n_clusters=2, n_init=10, random_state=0).fit(X)

    # Count labels per track — majority vote per track
    track_label_counts: dict[int, dict[int, int]] = {}
    for (tid, _), label in zip(all_hists, km.labels_):
        track_label_counts.setdefault(tid, {})
        track_label_counts[tid][label] = track_label_counts[tid].get(label, 0) + 1

    # Map cluster labels to team names
    label_to_team: dict[int, str]
    if roster:
        # Match cluster centers to roster colors via HSV histogram of pure color
        home_bgr = _hex_to_bgr(roster.home.color)
        away_bgr = _hex_to_bgr(roster.away.color)
        # Create synthetic histogram for each roster color
        home_patch = np.full((10, 10, 3), home_bgr, dtype=np.uint8)
        away_patch = np.full((10, 10, 3), away_bgr, dtype=np.uint8)
        home_hist = _hsv_histogram(home_patch)
        away_hist = _hsv_histogram(away_patch)  # noqa: F841 — kept for symmetry

        c0 = km.cluster_centers_[0]
        c1 = km.cluster_centers_[1]
        d0_home = np.linalg.norm(c0 - home_hist)
        d1_home = np.linalg.norm(c1 - home_hist)

        if d0_home <= d1_home:
            label_to_team = {0: "team_a", 1: "team_b"}
        else:
            label_to_team = {1: "team_a", 0: "team_b"}
    else:
        label_to_team = {0: "team_a", 1: "team_b"}

    # Assign majority label per track
    for tid, profile in tracks.items():
        counts = track_label_counts.get(tid, {})
        if not counts:
            profile.team = "team_a"
            continue
        majority_label = max(counts, key=counts.get)
        profile.team = label_to_team[majority_label]
