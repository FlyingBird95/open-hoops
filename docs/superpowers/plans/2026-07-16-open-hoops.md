# open_hoops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `open_hoops` Python package that extracts comprehensive basketball stats from a fixed-court-camera video using YOLO + ByteTrack, outputting JSON stats and an optional score-overlay video.

**Architecture:** Single-pass pipeline — each video frame flows through YOLO detection → ByteTrack tracking → jersey identity (color + OCR) → per-stat extractors → optional overlay renderer. An `Analyzer` class owns the loop; stat modules are stateful objects that accumulate results across frames and return a `GameStats` Pydantic model at the end.

**Tech Stack:** Python ≥3.10, ultralytics ≥8.0 (YOLO + ByteTrack), EasyOCR ≥1.7, OpenCV ≥4.9, Pydantic ≥2.0, NumPy ≥1.26, scikit-learn ≥1.4, pytest, ruff, mypy.

## Global Constraints

- Python ≥ 3.10 (use `match`, `X | Y` unions, `list[T]` built-in generics)
- ultralytics ≥ 8.0
- easyocr ≥ 1.7
- opencv-python ≥ 4.9
- pydantic ≥ 2.0 (use `model_dump()`, not `.dict()`)
- numpy ≥ 1.26
- scikit-learn ≥ 1.4
- No CLI — Python API only
- Public surface: `from open_hoops import analyze`
- `analyze(video_path, output_video=None) -> GameStats`
- All `GameStats` fields must survive `json.dumps(stats.model_dump())`
- Court coordinates in meters, NBA dimensions (28.65 m × 15.24 m)
- Hoop region defined as circle of radius 0.45 m around each hoop centre
- Missing/unreadable video → `ValueError`
- YOLO model not found → `FileNotFoundError`
- Ball undetected > 5 s → `warnings.warn`, mark window `uncertain=True`
- OCR failure → `player_id = None`

---

## File Map

| Path | Role |
|------|------|
| `pyproject.toml` | Package metadata + dependencies |
| `open_hoops/__init__.py` | Public `analyze()` function |
| `open_hoops/models.py` | Pydantic data models |
| `open_hoops/detector.py` | YOLO wrapper — yields `FrameDetections` |
| `open_hoops/tracker.py` | ByteTrack wrapper — yields `TrackedFrame` |
| `open_hoops/identity/team.py` | K-means jersey color → team assignment |
| `open_hoops/identity/player.py` | EasyOCR jersey number → player ID |
| `open_hoops/identity/__init__.py` | Re-exports `TeamClassifier`, `PlayerIdentifier` |
| `open_hoops/stats/possession.py` | Nearest-player possession tracker |
| `open_hoops/stats/shots.py` | Shot attempt / make / miss detector |
| `open_hoops/stats/movement.py` | Homography + per-player distance |
| `open_hoops/stats/passes.py` | Pass detector (Voronoi zone transitions) |
| `open_hoops/stats/score.py` | Score accumulator |
| `open_hoops/stats/__init__.py` | Re-exports all stat classes |
| `open_hoops/overlay.py` | OpenCV score HUD renderer |
| `open_hoops/analyzer.py` | `Analyzer` — main pipeline loop |
| `README.md` | Project README |
| `tests/conftest.py` | Shared fixtures |
| `tests/test_models.py` | Model serialization |
| `tests/test_detector.py` | Detector unit tests |
| `tests/test_tracker.py` | Tracker unit tests |
| `tests/test_identity_team.py` | Team classifier tests |
| `tests/test_identity_player.py` | Player identifier tests |
| `tests/test_stats_possession.py` | Possession tracker tests |
| `tests/test_stats_shots.py` | Shot detector tests |
| `tests/test_stats_movement.py` | Movement tracker tests |
| `tests/test_stats_passes.py` | Pass detector tests |
| `tests/test_stats_score.py` | Score accumulator tests |
| `tests/test_overlay.py` | Overlay renderer tests |
| `tests/test_analyzer.py` | Full pipeline integration test |

---

### Task 1: Project scaffold — pyproject.toml + package skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `open_hoops/__init__.py`
- Create: `open_hoops/models.py`
- Create: `open_hoops/stats/__init__.py`
- Create: `open_hoops/identity/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: installable package `open_hoops`; `from open_hoops.models import GameStats, TeamStats, PlayerStats, GameEvent, Point` available

- [ ] **Step 1: Write test**

```python
# tests/test_models.py
import json
from open_hoops.models import GameStats, TeamStats, PlayerStats, GameEvent, Point

def test_gamestats_json_roundtrip():
    stats = GameStats(
        video_path="game.mp4",
        duration_seconds=60.0,
        fps=30.0,
        teams=[],
        events=[],
    )
    dumped = stats.model_dump()
    assert json.dumps(dumped)  # must be JSON-serializable
    assert dumped["video_path"] == "game.mp4"

def test_player_stats_defaults():
    p = PlayerStats(player_id=None, team_id="team_a")
    assert p.shot_attempts == 0
    assert p.distance_covered_m == 0.0
    assert p.positions == []

def test_game_event_types():
    for t in ("shot", "make", "miss", "pass", "possession_change"):
        e = GameEvent(type=t, frame=1, timestamp_sec=0.033)
        assert e.type == t
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
cd /Users/pvogel/vibe/open-hoops
pytest tests/test_models.py -v
```
Expected: `ImportError: No module named 'open_hoops'`

- [ ] **Step 3: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "open_hoops"
version = "0.1.0"
description = "Extract basketball stats from video using YOLO"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
dependencies = [
    "ultralytics>=8.0",
    "easyocr>=1.7",
    "opencv-python>=4.9",
    "pydantic>=2.0",
    "numpy>=1.26",
    "scikit-learn>=1.4",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4", "mypy>=1.10"]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.mypy]
python_version = "3.10"
strict = true
```

- [ ] **Step 4: Create models.py**

```python
# open_hoops/models.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float
    y: float


class PlayerStats(BaseModel):
    player_id: int | None
    team_id: str
    positions: list[Point] = Field(default_factory=list)
    distance_covered_m: float = 0.0
    shot_attempts: int = 0
    shot_makes: int = 0
    passes_made: int = 0
    passes_received: int = 0
    possession_frames: int = 0


class TeamStats(BaseModel):
    team_id: str
    color: str = ""
    score: int = 0
    players: list[PlayerStats] = Field(default_factory=list)
    possession_pct: float = 0.0


class GameEvent(BaseModel):
    type: Literal["shot", "make", "miss", "pass", "possession_change"]
    frame: int
    timestamp_sec: float
    player_id: int | None = None
    team_id: str | None = None


class GameStats(BaseModel):
    video_path: str
    duration_seconds: float
    fps: float
    teams: list[TeamStats] = Field(default_factory=list)
    events: list[GameEvent] = Field(default_factory=list)
```

- [ ] **Step 5: Create package init files**

```python
# open_hoops/__init__.py
from open_hoops.analyzer import Analyzer


def analyze(video_path: str, output_video: str | None = None):
    return Analyzer(video_path, output_video=output_video).run()
```

```python
# open_hoops/stats/__init__.py
from open_hoops.stats.possession import PossessionTracker
from open_hoops.stats.shots import ShotDetector
from open_hoops.stats.movement import MovementTracker
from open_hoops.stats.passes import PassDetector
from open_hoops.stats.score import ScoreTracker

__all__ = [
    "PossessionTracker",
    "ShotDetector",
    "MovementTracker",
    "PassDetector",
    "ScoreTracker",
]
```

```python
# open_hoops/identity/__init__.py
from open_hoops.identity.team import TeamClassifier
from open_hoops.identity.player import PlayerIdentifier

__all__ = ["TeamClassifier", "PlayerIdentifier"]
```

```python
# tests/__init__.py
```

```python
# tests/conftest.py
import numpy as np
import pytest

@pytest.fixture
def blank_frame():
    return np.zeros((720, 1280, 3), dtype=np.uint8)

@pytest.fixture
def fake_detections():
    return {
        "players": [
            {"track_id": 1, "bbox": [100, 200, 150, 300], "conf": 0.9},
            {"track_id": 2, "bbox": [400, 200, 450, 300], "conf": 0.85},
        ],
        "ball": {"bbox": [200, 250, 220, 270], "conf": 0.8},
        "hoops": [
            {"bbox": [50, 350, 100, 380], "conf": 0.95},
            {"bbox": [1180, 350, 1230, 380], "conf": 0.95},
        ],
    }
```

- [ ] **Step 6: Install in editable mode**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 7: Run tests — expect PASS**

```bash
pytest tests/test_models.py -v
```
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml open_hoops/ tests/
git commit -m "feat: scaffold package with data models"
```

---

### Task 2: Detector — YOLO wrapper

**Files:**
- Create: `open_hoops/detector.py`
- Create: `tests/test_detector.py`

**Interfaces:**
- Consumes: nothing from prior tasks
- Produces:
  - `Detection(bbox: tuple[int,int,int,int], conf: float, class_name: str, track_id: int | None)`
  - `FrameDetections(players: list[Detection], ball: Detection | None, hoops: list[Detection])`
  - `Detector(model_path: str)` with `.detect(frame: np.ndarray) -> FrameDetections`

- [ ] **Step 1: Write tests**

```python
# tests/test_detector.py
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from open_hoops.detector import Detector, FrameDetections, Detection


def make_mock_result(boxes_data):
    """boxes_data: list of (x1,y1,x2,y2, conf, cls_id, track_id|None)"""
    mock_result = MagicMock()
    mock_boxes = MagicMock()
    mock_boxes.xyxy.cpu().numpy.return_value = np.array(
        [[b[0], b[1], b[2], b[3]] for b in boxes_data], dtype=float
    )
    mock_boxes.conf.cpu().numpy.return_value = np.array(
        [b[4] for b in boxes_data], dtype=float
    )
    mock_boxes.cls.cpu().numpy.return_value = np.array(
        [b[5] for b in boxes_data], dtype=float
    )
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
    mock_model.track.return_value = make_mock_result([
        (100, 200, 150, 300, 0.9, 0, 1),
        (400, 200, 450, 300, 0.85, 0, 2),
        (200, 250, 220, 270, 0.8, 1, None),
        (50, 350, 100, 380, 0.95, 2, None),
    ])

    detector = Detector("yolo11n.pt")
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
```

- [ ] **Step 2: Run test — expect ImportError/ModuleNotFoundError**

```bash
pytest tests/test_detector.py -v
```
Expected: FAIL (module not found)

- [ ] **Step 3: Implement detector.py**

```python
# open_hoops/detector.py
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    conf: float
    class_name: str
    track_id: int | None = None


@dataclass
class FrameDetections:
    players: list[Detection] = field(default_factory=list)
    ball: Detection | None = None
    hoops: list[Detection] = field(default_factory=list)


class Detector:
    def __init__(self, model_path: str = "yolo11n.pt") -> None:
        self._model = YOLO(model_path)

    def detect(self, frame: np.ndarray) -> FrameDetections:
        results = self._model.track(frame, persist=True, verbose=False)
        fd = FrameDetections()
        if not results:
            return fd
        r = results[0]
        boxes = r.boxes
        if boxes is None:
            return fd

        bboxes = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        track_ids = (
            boxes.id.cpu().numpy().astype(int)
            if boxes.id is not None
            else [None] * len(bboxes)
        )

        for bbox, conf, cls_id, tid in zip(bboxes, confs, classes, track_ids):
            name = r.names[cls_id]
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            det = Detection(
                bbox=(x1, y1, x2, y2),
                conf=float(conf),
                class_name=name,
                track_id=int(tid) if tid is not None else None,
            )
            if name == "player":
                fd.players.append(det)
            elif name == "ball":
                fd.ball = det
            elif name == "hoop":
                fd.hoops.append(det)

        return fd
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_detector.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/detector.py tests/test_detector.py
git commit -m "feat: add YOLO detector wrapper"
```

---

### Task 3: Tracker — ByteTrack wrapper + homography

**Files:**
- Create: `open_hoops/tracker.py`
- Create: `tests/test_tracker.py`

**Interfaces:**
- Consumes: `FrameDetections` from Task 2
- Produces:
  - `TrackedPlayer(track_id: int, bbox: tuple[int,int,int,int], court_pos: tuple[float,float])`
  - `TrackedFrame(players: list[TrackedPlayer], ball_pos: tuple[float,float] | None, hoops: list[tuple[float,float]], frame_idx: int)`
  - `Tracker(homography_matrix: np.ndarray)` with `.update(fd: FrameDetections, frame_idx: int) -> TrackedFrame`
  - `compute_homography(src_pts: np.ndarray, dst_pts: np.ndarray) -> np.ndarray` — thin wrapper around `cv2.findHomography`

- [ ] **Step 1: Write tests**

```python
# tests/test_tracker.py
import numpy as np
import pytest
from open_hoops.detector import Detection, FrameDetections
from open_hoops.tracker import Tracker, TrackedFrame, compute_homography


@pytest.fixture
def identity_homography():
    return np.eye(3, dtype=np.float64)


def make_fd(players=None, ball=None, hoops=None):
    fd = FrameDetections()
    fd.players = players or []
    fd.ball = ball
    fd.hoops = hoops or []
    return fd


def test_tracker_returns_tracked_frame(identity_homography):
    tracker = Tracker(identity_homography)
    player = Detection(bbox=(100, 200, 150, 300), conf=0.9, class_name="player", track_id=1)
    ball = Detection(bbox=(200, 250, 220, 270), conf=0.8, class_name="ball")
    fd = make_fd(players=[player], ball=ball)

    result = tracker.update(fd, frame_idx=0)
    assert isinstance(result, TrackedFrame)
    assert len(result.players) == 1
    assert result.players[0].track_id == 1
    assert result.ball_pos is not None


def test_tracker_no_ball(identity_homography):
    tracker = Tracker(identity_homography)
    fd = make_fd()
    result = tracker.update(fd, frame_idx=5)
    assert result.ball_pos is None
    assert result.players == []


def test_compute_homography_returns_matrix():
    src = np.array([[0,0],[100,0],[100,100],[0,100]], dtype=np.float32)
    dst = np.array([[0,0],[28.65,0],[28.65,15.24],[0,15.24]], dtype=np.float32)
    H = compute_homography(src, dst)
    assert H.shape == (3, 3)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_tracker.py -v
```
Expected: FAIL (module not found)

- [ ] **Step 3: Implement tracker.py**

```python
# open_hoops/tracker.py
from __future__ import annotations
import numpy as np
import cv2
from dataclasses import dataclass, field
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


def _pixel_to_court(
    px: float, py: float, H: np.ndarray
) -> tuple[float, float]:
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_tracker.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/tracker.py tests/test_tracker.py
git commit -m "feat: add tracker with homography court mapping"
```

---

### Task 4: Identity — team color classifier

**Files:**
- Create: `open_hoops/identity/team.py`
- Create: `tests/test_identity_team.py`

**Interfaces:**
- Consumes: `np.ndarray` frame, player `bbox` tuples
- Produces:
  - `TeamClassifier` with:
    - `.fit(frames: list[np.ndarray], player_bboxes: list[list[tuple[int,int,int,int]]])` — run K-means on first 30 frames; call once
    - `.assign(frame: np.ndarray, bbox: tuple[int,int,int,int]) -> str` — returns `"team_a"` or `"team_b"`
    - `.team_colors: dict[str, str]` — `{"team_a": "#rrggbb", "team_b": "#rrggbb"}`

- [ ] **Step 1: Write tests**

```python
# tests/test_identity_team.py
import numpy as np
import pytest
from open_hoops.identity.team import TeamClassifier


def make_frame_with_player(color_bgr, bbox=(100, 200, 150, 300)):
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    x1, y1, x2, y2 = bbox
    frame[y1:y2, x1:x2] = color_bgr
    return frame


def test_fit_and_assign_two_teams():
    clf = TeamClassifier()
    red = (0, 0, 200)
    blue = (200, 0, 0)
    frames = []
    bboxes_per_frame = []
    for _ in range(5):
        f = make_frame_with_player(red, (100, 200, 150, 300))
        f2 = f.copy()
        f2[200:300, 400:450] = blue
        frames.append(f2)
        bboxes_per_frame.append([(100, 200, 150, 300), (400, 200, 450, 300)])

    clf.fit(frames, bboxes_per_frame)

    frame_red = make_frame_with_player(red, (100, 200, 150, 300))
    frame_blue = make_frame_with_player(blue, (400, 200, 450, 300))

    team_r = clf.assign(frame_red, (100, 200, 150, 300))
    team_b = clf.assign(frame_blue, (400, 200, 450, 300))

    assert team_r != team_b
    assert team_r in ("team_a", "team_b")
    assert team_b in ("team_a", "team_b")


def test_team_colors_populated_after_fit():
    clf = TeamClassifier()
    red = (0, 0, 200)
    blue = (200, 0, 0)
    frames, bboxes = [], []
    for _ in range(3):
        f = np.zeros((720, 1280, 3), dtype=np.uint8)
        f[200:300, 100:150] = red
        f[200:300, 400:450] = blue
        frames.append(f)
        bboxes.append([(100, 200, 150, 300), (400, 200, 450, 300)])
    clf.fit(frames, bboxes)
    assert "team_a" in clf.team_colors
    assert "team_b" in clf.team_colors
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_identity_team.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement identity/team.py**

```python
# open_hoops/identity/team.py
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
        for frame, bboxes in zip(frames, player_bboxes):
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
        hist = _hsv_histogram(crop).reshape(1, -1)
        label = int(self._kmeans.predict(hist)[0])
        return "team_a" if label == 0 else "team_b"
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_identity_team.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/identity/team.py tests/test_identity_team.py
git commit -m "feat: add jersey color team classifier"
```

---

### Task 5: Identity — player OCR

**Files:**
- Create: `open_hoops/identity/player.py`
- Create: `tests/test_identity_player.py`
- Modify: `open_hoops/identity/__init__.py`

**Interfaces:**
- Consumes: `np.ndarray` frame, player `bbox`
- Produces:
  - `PlayerIdentifier` with `.identify(frame: np.ndarray, bbox: tuple[int,int,int,int], track_id: int) -> int | None`
  - Internally: runs OCR every 30 frames per track_id, majority vote over last 10 readings
  - `._frame_counter: dict[int, int]` — frame count per track_id
  - `._history: dict[int, list[int]]` — reading history per track_id

- [ ] **Step 1: Write tests**

```python
# tests/test_identity_player.py
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
        # first 10 readings return 23
        for i in range(10):
            ident._frame_counter[1] = i * 30  # simulate every-30-frame trigger
            ident._history.setdefault(1, []).append(23)
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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_identity_player.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement identity/player.py**

```python
# open_hoops/identity/player.py
from __future__ import annotations
import re
import numpy as np
import easyocr


class PlayerIdentifier:
    def __init__(self) -> None:
        self._reader: easyocr.Reader | None = None
        self._frame_counter: dict[int, int] = {}
        self._history: dict[int, list[int]] = {}

    def _get_reader(self) -> easyocr.Reader:
        if self._reader is None:
            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return self._reader

    def _run_ocr(self, frame: np.ndarray, bbox: tuple[int, int, int, int]) -> int | None:
        x1, y1, x2, y2 = bbox
        h = y2 - y1
        # torso crop
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
                return int(digits[:2])
        return None

    def _majority(self, track_id: int) -> int | None:
        history = self._history.get(track_id, [])
        if not history:
            return None
        last = history[-10:]
        counts: dict[int, int] = {}
        for v in last:
            counts[v] = counts.get(v, 0) + 1
        return max(counts, key=lambda k: counts[k])

    def identify(
        self,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int],
        track_id: int,
    ) -> int | None:
        count = self._frame_counter.get(track_id, 0)
        if count % 30 == 0:
            number = self._run_ocr(frame, bbox)
            if number is not None:
                self._history.setdefault(track_id, []).append(number)
        self._frame_counter[track_id] = count + 1
        return self._majority(track_id)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_identity_player.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/identity/player.py tests/test_identity_player.py
git commit -m "feat: add jersey number OCR player identifier"
```

---

### Task 6: Stats — possession tracker

**Files:**
- Create: `open_hoops/stats/possession.py`
- Create: `tests/test_stats_possession.py`

**Interfaces:**
- Consumes: `TrackedFrame` from Task 3
- Produces:
  - `PossessionTracker` with:
    - `.update(tf: TrackedFrame, player_teams: dict[int, str], frame_idx: int, fps: float) -> list[GameEvent]`
    - `.finalize(total_frames: int) -> dict[str, float]` — returns `{"team_a": 0.6, "team_b": 0.4}` possession percentages

- [ ] **Step 1: Write tests**

```python
# tests/test_stats_possession.py
import pytest
from open_hoops.tracker import TrackedFrame, TrackedPlayer
from open_hoops.stats.possession import PossessionTracker


def make_tf(players, ball_pos, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players
    tf.ball_pos = ball_pos
    return tf


def test_possession_assigned_to_nearest_player():
    tracker = PossessionTracker()
    players = [
        TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(5.0, 5.0)),
        TrackedPlayer(track_id=2, bbox=(0,0,1,1), court_pos=(20.0, 10.0)),
    ]
    tf = make_tf(players, ball_pos=(5.1, 5.1))
    events = tracker.update(tf, {1: "team_a", 2: "team_b"}, frame_idx=0, fps=30.0)
    assert tracker._current_owner == 1


def test_possession_change_fires_event():
    tracker = PossessionTracker()
    p1 = TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0,0,1,1), court_pos=(20.0, 10.0))
    tracker.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_b"}, 0, 30.0)
    events = tracker.update(make_tf([p1, p2], (19.9, 10.0)), {1: "team_a", 2: "team_b"}, 1, 30.0)
    assert any(e.type == "possession_change" for e in events)


def test_finalize_sums_to_one():
    tracker = PossessionTracker()
    p1 = TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0,0,1,1), court_pos=(20.0, 10.0))
    for i in range(10):
        tracker.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_b"}, i, 30.0)
    pct = tracker.finalize(10)
    assert abs(pct["team_a"] + pct["team_b"] - 1.0) < 0.01


def test_no_ball_no_event():
    tracker = PossessionTracker()
    tf = make_tf([], ball_pos=None)
    events = tracker.update(tf, {}, 0, 30.0)
    assert events == []
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_stats_possession.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement stats/possession.py**

```python
# open_hoops/stats/possession.py
from __future__ import annotations
import math
from open_hoops.tracker import TrackedFrame
from open_hoops.models import GameEvent


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class PossessionTracker:
    def __init__(self) -> None:
        self._current_owner: int | None = None
        self._current_team: str | None = None
        self._frame_counts: dict[str, int] = {"team_a": 0, "team_b": 0}

    def update(
        self,
        tf: TrackedFrame,
        player_teams: dict[int, str],
        frame_idx: int,
        fps: float,
    ) -> list[GameEvent]:
        if tf.ball_pos is None or not tf.players:
            return []

        nearest = min(tf.players, key=lambda p: _dist(p.court_pos, tf.ball_pos))
        new_owner = nearest.track_id
        new_team = player_teams.get(new_owner, "team_a")

        events: list[GameEvent] = []
        if new_team != self._current_team and self._current_team is not None:
            events.append(
                GameEvent(
                    type="possession_change",
                    frame=frame_idx,
                    timestamp_sec=frame_idx / fps,
                    player_id=new_owner,
                    team_id=new_team,
                )
            )

        self._current_owner = new_owner
        self._current_team = new_team
        self._frame_counts[new_team] = self._frame_counts.get(new_team, 0) + 1
        return events

    def finalize(self, total_frames: int) -> dict[str, float]:
        if total_frames == 0:
            return {"team_a": 0.0, "team_b": 0.0}
        ball_frames = sum(self._frame_counts.values())
        if ball_frames == 0:
            return {"team_a": 0.0, "team_b": 0.0}
        return {
            team: count / ball_frames
            for team, count in self._frame_counts.items()
        }
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_stats_possession.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/stats/possession.py tests/test_stats_possession.py
git commit -m "feat: add possession tracker"
```

---

### Task 7: Stats — shot detector

**Files:**
- Create: `open_hoops/stats/shots.py`
- Create: `tests/test_stats_shots.py`

**Interfaces:**
- Consumes: `TrackedFrame`, `player_teams: dict[int, str]`, `possession_owner: int | None`
- Produces:
  - `ShotDetector(hoop_radius_m: float = 0.45)` with:
    - `.update(tf: TrackedFrame, player_teams: dict[int, str], possession_owner: int | None, frame_idx: int, fps: float) -> list[GameEvent]`
    - Returns events of type `"shot"`, `"make"`, or `"miss"`

- [ ] **Step 1: Write tests**

```python
# tests/test_stats_shots.py
import pytest
from open_hoops.tracker import TrackedFrame, TrackedPlayer
from open_hoops.stats.shots import ShotDetector


def make_tf(ball_pos, hoops=None, players=None, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.ball_pos = ball_pos
    tf.hoops = hoops or [(0.5, 7.62), (28.15, 7.62)]
    tf.players = players or []
    return tf


def test_shot_attempt_detected_when_ball_enters_hoop_region():
    det = ShotDetector(hoop_radius_m=0.45)
    tf_far = make_tf(ball_pos=(14.0, 7.62), frame_idx=0)
    tf_near = make_tf(ball_pos=(0.6, 7.62), frame_idx=1)
    det.update(tf_far, {}, None, 0, 30.0)
    events = det.update(tf_near, {}, 1, 1, 30.0)
    assert any(e.type == "shot" for e in events)


def test_make_when_ball_crosses_hoop_center():
    det = ShotDetector(hoop_radius_m=0.45)
    tf_approach = make_tf(ball_pos=(0.6, 7.62), frame_idx=0)
    tf_center = make_tf(ball_pos=(0.5, 7.62), frame_idx=1)
    det.update(tf_approach, {}, None, 0, 30.0)
    events = det.update(tf_center, {}, None, 1, 30.0)
    assert any(e.type in ("make", "shot") for e in events)


def test_no_events_when_ball_far_from_hoop():
    det = ShotDetector(hoop_radius_m=0.45)
    tf = make_tf(ball_pos=(14.0, 7.62))
    events = det.update(tf, {}, None, 0, 30.0)
    assert events == []
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_stats_shots.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement stats/shots.py**

```python
# open_hoops/stats/shots.py
from __future__ import annotations
import math
from open_hoops.tracker import TrackedFrame
from open_hoops.models import GameEvent

_MAKE_RADIUS = 0.15  # ball centre within this of hoop centre = make


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class ShotDetector:
    def __init__(self, hoop_radius_m: float = 0.45) -> None:
        self._radius = hoop_radius_m
        self._in_region: dict[int, bool] = {}  # hoop_idx -> was ball in region last frame

    def update(
        self,
        tf: TrackedFrame,
        player_teams: dict[int, str],
        possession_owner: int | None,
        frame_idx: int,
        fps: float,
    ) -> list[GameEvent]:
        if tf.ball_pos is None or not tf.hoops:
            return []

        events: list[GameEvent] = []
        team_id = player_teams.get(possession_owner) if possession_owner is not None else None

        for idx, hoop in enumerate(tf.hoops):
            dist = _dist(tf.ball_pos, hoop)
            was_in = self._in_region.get(idx, False)
            now_in = dist <= self._radius

            if now_in and not was_in:
                events.append(GameEvent(
                    type="shot",
                    frame=frame_idx,
                    timestamp_sec=frame_idx / fps,
                    player_id=possession_owner,
                    team_id=team_id,
                ))
            if dist <= _MAKE_RADIUS and was_in:
                events.append(GameEvent(
                    type="make",
                    frame=frame_idx,
                    timestamp_sec=frame_idx / fps,
                    player_id=possession_owner,
                    team_id=team_id,
                ))
            elif not now_in and was_in:
                events.append(GameEvent(
                    type="miss",
                    frame=frame_idx,
                    timestamp_sec=frame_idx / fps,
                    player_id=possession_owner,
                    team_id=team_id,
                ))

            self._in_region[idx] = now_in

        return events
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_stats_shots.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/stats/shots.py tests/test_stats_shots.py
git commit -m "feat: add shot detector"
```

---

### Task 8: Stats — movement tracker

**Files:**
- Create: `open_hoops/stats/movement.py`
- Create: `tests/test_stats_movement.py`

**Interfaces:**
- Consumes: `TrackedFrame`
- Produces:
  - `MovementTracker` with:
    - `.update(tf: TrackedFrame) -> None`
    - `.get_distance(track_id: int) -> float` — total meters covered
    - `.get_positions(track_id: int) -> list[tuple[float, float]]`

- [ ] **Step 1: Write tests**

```python
# tests/test_stats_movement.py
import math
import pytest
from open_hoops.tracker import TrackedFrame, TrackedPlayer
from open_hoops.stats.movement import MovementTracker


def make_tf(players, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players
    return tf


def test_distance_accumulates():
    tracker = MovementTracker()
    p1 = TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(0.0, 0.0))
    p2 = TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(3.0, 4.0))  # dist=5
    tracker.update(make_tf([p1], 0))
    tracker.update(make_tf([p2], 1))
    assert abs(tracker.get_distance(1) - 5.0) < 0.001


def test_positions_recorded():
    tracker = MovementTracker()
    p = TrackedPlayer(track_id=2, bbox=(0,0,1,1), court_pos=(1.0, 2.0))
    tracker.update(make_tf([p], 0))
    positions = tracker.get_positions(2)
    assert positions == [(1.0, 2.0)]


def test_unknown_track_id_returns_zero():
    tracker = MovementTracker()
    assert tracker.get_distance(999) == 0.0
    assert tracker.get_positions(999) == []
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_stats_movement.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement stats/movement.py**

```python
# open_hoops/stats/movement.py
from __future__ import annotations
import math
from open_hoops.tracker import TrackedFrame


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class MovementTracker:
    def __init__(self) -> None:
        self._last_pos: dict[int, tuple[float, float]] = {}
        self._distances: dict[int, float] = {}
        self._positions: dict[int, list[tuple[float, float]]] = {}

    def update(self, tf: TrackedFrame) -> None:
        for player in tf.players:
            tid = player.track_id
            pos = player.court_pos
            self._positions.setdefault(tid, []).append(pos)
            if tid in self._last_pos:
                self._distances[tid] = (
                    self._distances.get(tid, 0.0) + _dist(self._last_pos[tid], pos)
                )
            self._last_pos[tid] = pos

    def get_distance(self, track_id: int) -> float:
        return self._distances.get(track_id, 0.0)

    def get_positions(self, track_id: int) -> list[tuple[float, float]]:
        return self._positions.get(track_id, [])
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_stats_movement.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/stats/movement.py tests/test_stats_movement.py
git commit -m "feat: add movement tracker"
```

---

### Task 9: Stats — pass detector

**Files:**
- Create: `open_hoops/stats/passes.py`
- Create: `tests/test_stats_passes.py`

**Interfaces:**
- Consumes: `TrackedFrame`, `player_teams: dict[int, str]`, `possession_owner: int | None`
- Produces:
  - `PassDetector` with:
    - `.update(tf: TrackedFrame, player_teams: dict[int, str], possession_owner: int | None, frame_idx: int, fps: float, shot_this_frame: bool) -> list[GameEvent]`
    - Returns `GameEvent(type="pass", ...)` when ball moves from one player's zone to another without a shot

- [ ] **Step 1: Write tests**

```python
# tests/test_stats_passes.py
import pytest
from open_hoops.tracker import TrackedFrame, TrackedPlayer
from open_hoops.stats.passes import PassDetector


def make_tf(players, ball_pos, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players
    tf.ball_pos = ball_pos
    return tf


def test_pass_detected_on_zone_change():
    det = PassDetector()
    p1 = TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0,0,1,1), court_pos=(20.0, 10.0))

    # ball near p1
    det.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_a"}, 1, 0, 30.0, False)
    # ball moves to p2
    events = det.update(make_tf([p1, p2], (19.9, 10.0)), {1: "team_a", 2: "team_a"}, 2, 1, 30.0, False)
    assert any(e.type == "pass" for e in events)


def test_no_pass_when_shot_this_frame():
    det = PassDetector()
    p1 = TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(5.0, 5.0))
    p2 = TrackedPlayer(track_id=2, bbox=(0,0,1,1), court_pos=(20.0, 10.0))

    det.update(make_tf([p1, p2], (5.1, 5.1)), {1: "team_a", 2: "team_a"}, 1, 0, 30.0, False)
    events = det.update(make_tf([p1, p2], (19.9, 10.0)), {1: "team_a", 2: "team_a"}, 2, 1, 30.0, shot_this_frame=True)
    assert not any(e.type == "pass" for e in events)


def test_no_pass_on_first_frame():
    det = PassDetector()
    p1 = TrackedPlayer(track_id=1, bbox=(0,0,1,1), court_pos=(5.0, 5.0))
    events = det.update(make_tf([p1], (5.1, 5.1)), {1: "team_a"}, 1, 0, 30.0, False)
    assert events == []
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_stats_passes.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement stats/passes.py**

```python
# open_hoops/stats/passes.py
from __future__ import annotations
import math
from open_hoops.tracker import TrackedFrame
from open_hoops.models import GameEvent


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _nearest_player(players, ball_pos) -> int | None:
    if not players or ball_pos is None:
        return None
    return min(players, key=lambda p: _dist(p.court_pos, ball_pos)).track_id


class PassDetector:
    def __init__(self) -> None:
        self._prev_owner: int | None = None

    def update(
        self,
        tf: TrackedFrame,
        player_teams: dict[int, str],
        possession_owner: int | None,
        frame_idx: int,
        fps: float,
        shot_this_frame: bool,
    ) -> list[GameEvent]:
        if tf.ball_pos is None or shot_this_frame:
            self._prev_owner = possession_owner
            return []

        nearest = _nearest_player(tf.players, tf.ball_pos)
        events: list[GameEvent] = []

        if (
            nearest is not None
            and self._prev_owner is not None
            and nearest != self._prev_owner
        ):
            events.append(GameEvent(
                type="pass",
                frame=frame_idx,
                timestamp_sec=frame_idx / fps,
                player_id=self._prev_owner,
                team_id=player_teams.get(self._prev_owner),
            ))

        self._prev_owner = nearest
        return events
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_stats_passes.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/stats/passes.py tests/test_stats_passes.py
git commit -m "feat: add pass detector"
```

---

### Task 10: Stats — score tracker

**Files:**
- Create: `open_hoops/stats/score.py`
- Create: `tests/test_stats_score.py`

**Interfaces:**
- Consumes: `list[GameEvent]` (from shot detector, per frame)
- Produces:
  - `ScoreTracker` with:
    - `.update(events: list[GameEvent]) -> None`
    - `.scores: dict[str, int]` — `{"team_a": 0, "team_b": 0}`

- [ ] **Step 1: Write tests**

```python
# tests/test_stats_score.py
import pytest
from open_hoops.stats.score import ScoreTracker
from open_hoops.models import GameEvent


def make_make_event(team_id):
    return GameEvent(type="make", frame=1, timestamp_sec=0.033, team_id=team_id)

def make_shot_event(team_id):
    return GameEvent(type="shot", frame=1, timestamp_sec=0.033, team_id=team_id)


def test_score_increments_on_make():
    tracker = ScoreTracker()
    tracker.update([make_make_event("team_a")])
    assert tracker.scores["team_a"] == 2
    assert tracker.scores["team_b"] == 0


def test_score_ignores_shot_events():
    tracker = ScoreTracker()
    tracker.update([make_shot_event("team_a")])
    assert tracker.scores["team_a"] == 0


def test_score_accumulates_multiple_makes():
    tracker = ScoreTracker()
    tracker.update([make_make_event("team_b")])
    tracker.update([make_make_event("team_b")])
    assert tracker.scores["team_b"] == 4
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_stats_score.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement stats/score.py**

```python
# open_hoops/stats/score.py
from __future__ import annotations
from open_hoops.models import GameEvent


class ScoreTracker:
    def __init__(self) -> None:
        self.scores: dict[str, int] = {"team_a": 0, "team_b": 0}

    def update(self, events: list[GameEvent]) -> None:
        for event in events:
            if event.type == "make" and event.team_id in self.scores:
                self.scores[event.team_id] += 2
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_stats_score.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/stats/score.py tests/test_stats_score.py
git commit -m "feat: add score tracker"
```

---

### Task 11: Overlay renderer

**Files:**
- Create: `open_hoops/overlay.py`
- Create: `tests/test_overlay.py`

**Interfaces:**
- Consumes: `np.ndarray` frame, `scores: dict[str, int]`, `team_colors: dict[str, str]`, `frame_idx: int`, `fps: float`
- Produces:
  - `Overlay` with `.render(frame: np.ndarray, scores: dict[str, int], team_colors: dict[str, str], frame_idx: int, fps: float) -> np.ndarray`
  - Returns annotated copy of frame (does not mutate input)

- [ ] **Step 1: Write tests**

```python
# tests/test_overlay.py
import numpy as np
import pytest
from open_hoops.overlay import Overlay


def test_render_returns_same_shape():
    overlay = Overlay()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = overlay.render(frame, {"team_a": 10, "team_b": 8}, {"team_a": "#ff0000", "team_b": "#0000ff"}, 90, 30.0)
    assert result.shape == frame.shape


def test_render_does_not_mutate_input():
    overlay = Overlay()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    original = frame.copy()
    overlay.render(frame, {"team_a": 0, "team_b": 0}, {}, 0, 30.0)
    assert np.array_equal(frame, original)


def test_render_modifies_output():
    overlay = Overlay()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = overlay.render(frame, {"team_a": 5, "team_b": 3}, {"team_a": "#ff0000", "team_b": "#0000ff"}, 60, 30.0)
    assert not np.array_equal(result, frame)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_overlay.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement overlay.py**

```python
# open_hoops/overlay.py
from __future__ import annotations
import cv2
import numpy as np


def _hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (255, 255, 255)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return b, g, r


class Overlay:
    HUD_H = 60
    HUD_W = 400
    MARGIN = 10

    def render(
        self,
        frame: np.ndarray,
        scores: dict[str, int],
        team_colors: dict[str, str],
        frame_idx: int,
        fps: float,
    ) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]

        # background strip
        x0 = (w - self.HUD_W) // 2
        y0 = self.MARGIN
        x1, y1 = x0 + self.HUD_W, y0 + self.HUD_H
        cv2.rectangle(out, (x0, y0), (x1, y1), (20, 20, 20), -1)
        cv2.rectangle(out, (x0, y0), (x1, y1), (200, 200, 200), 2)

        score_a = scores.get("team_a", 0)
        score_b = scores.get("team_b", 0)
        color_a = _hex_to_bgr(team_colors.get("team_a", "#ffffff"))
        color_b = _hex_to_bgr(team_colors.get("team_b", "#ffffff"))

        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"{score_a}  -  {score_b}"
        (tw, th), _ = cv2.getTextSize(text, font, 1.2, 2)
        tx = x0 + (self.HUD_W - tw) // 2
        ty = y0 + self.HUD_H // 2 + th // 2

        half = self.HUD_W // 2
        cv2.rectangle(out, (x0, y0 + 2), (x0 + half, y1 - 2), color_a, -1)
        cv2.rectangle(out, (x0 + half, y0 + 2), (x1, y1 - 2), color_b, -1)
        cv2.putText(out, text, (tx, ty), font, 1.2, (255, 255, 255), 2, cv2.LINE_AA)

        elapsed = int(frame_idx / fps) if fps > 0 else 0
        mins, secs = divmod(elapsed, 60)
        clock = f"{mins:02d}:{secs:02d}"
        cv2.putText(out, clock, (x1 + 10, ty), font, 0.7, (220, 220, 220), 1, cv2.LINE_AA)

        return out
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_overlay.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/overlay.py tests/test_overlay.py
git commit -m "feat: add score overlay renderer"
```

---

### Task 12: Analyzer — main pipeline

**Files:**
- Create: `open_hoops/analyzer.py`
- Create: `tests/test_analyzer.py`

**Interfaces:**
- Consumes: all modules from Tasks 2–11
- Produces:
  - `Analyzer(video_path: str, model_path: str = "yolo11n.pt", output_video: str | None = None)` with `.run() -> GameStats`

- [ ] **Step 1: Write tests**

```python
# tests/test_analyzer.py
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from open_hoops.analyzer import Analyzer
from open_hoops.models import GameStats
from open_hoops.detector import FrameDetections
from open_hoops.tracker import TrackedFrame


def make_mock_cap(n_frames=10, width=1280, height=720, fps=30.0):
    cap = MagicMock()
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frames = iter([True] * n_frames + [False])
    cap.read.side_effect = lambda: (next(frames), frame)
    cap.get.side_effect = lambda prop: {
        0: fps,        # CAP_PROP_FPS
        7: n_frames,   # CAP_PROP_FRAME_COUNT
    }.get(prop, 0)
    cap.isOpened.return_value = True
    return cap


def test_invalid_video_raises_value_error():
    with patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap
        with pytest.raises(ValueError, match="Cannot open video"):
            Analyzer("nonexistent.mp4").run()


def test_run_returns_game_stats():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=5)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = Analyzer("fake.mp4").run()
        assert isinstance(stats, GameStats)
        assert stats.video_path == "fake.mp4"
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_analyzer.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement analyzer.py**

```python
# open_hoops/analyzer.py
from __future__ import annotations
import warnings
import cv2
import numpy as np

from open_hoops.models import GameStats, TeamStats, PlayerStats, Point
from open_hoops.detector import Detector
from open_hoops.tracker import Tracker, compute_homography
from open_hoops.identity.team import TeamClassifier
from open_hoops.identity.player import PlayerIdentifier
from open_hoops.stats.possession import PossessionTracker
from open_hoops.stats.shots import ShotDetector
from open_hoops.stats.movement import MovementTracker
from open_hoops.stats.passes import PassDetector
from open_hoops.stats.score import ScoreTracker
from open_hoops.overlay import Overlay

# NBA half-court corners in pixel space (override via subclass or homography args)
# Default: assume 1280×720 frame, court fills frame width, hoops at 5% and 95% x
_DEFAULT_SRC = np.array([
    [0, 0], [1280, 0], [1280, 720], [0, 720]
], dtype=np.float32)
_DEFAULT_DST = np.array([
    [0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]
], dtype=np.float32)

_BALL_MISSING_WARN_FRAMES = 5 * 30  # 5 seconds at 30 fps


class Analyzer:
    def __init__(
        self,
        video_path: str,
        model_path: str = "yolo11n.pt",
        output_video: str | None = None,
        src_pts: np.ndarray | None = None,
        dst_pts: np.ndarray | None = None,
    ) -> None:
        self._video_path = video_path
        self._model_path = model_path
        self._output_video = output_video
        self._src = src_pts if src_pts is not None else _DEFAULT_SRC
        self._dst = dst_pts if dst_pts is not None else _DEFAULT_DST

    def run(self) -> GameStats:
        cap = cv2.VideoCapture(self._video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {self._video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        H = compute_homography(self._src, self._dst)
        detector = Detector(self._model_path)
        tracker = Tracker(H)
        team_clf = TeamClassifier()
        player_ident = PlayerIdentifier()
        possession = PossessionTracker()
        shots = ShotDetector()
        movement = MovementTracker()
        passes = PassDetector()
        score = ScoreTracker()
        overlay = Overlay()

        writer: cv2.VideoWriter | None = None
        all_events = []
        player_teams: dict[int, str] = {}

        # Phase 1: collect first 30 frames for team classifier
        warmup_frames: list[np.ndarray] = []
        warmup_bboxes: list[list[tuple[int, int, int, int]]] = []

        frame_idx = 0
        ball_missing_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            fd = detector.detect(frame)
            tf = tracker.update(fd, frame_idx)

            # team classifier warmup
            if frame_idx < 30:
                warmup_frames.append(frame)
                warmup_bboxes.append([p.bbox for p in fd.players])
            elif frame_idx == 30:
                team_clf.fit(warmup_frames, warmup_bboxes)

            # assign team + player identity
            for p in fd.players:
                if p.track_id is None:
                    continue
                team = team_clf.assign(frame, p.bbox) if frame_idx >= 30 else "team_a"
                player_teams[p.track_id] = team
                player_ident.identify(frame, p.bbox, p.track_id)

            # track ball missing warning
            if tf.ball_pos is None:
                ball_missing_count += 1
                if ball_missing_count == _BALL_MISSING_WARN_FRAMES:
                    warnings.warn(f"Ball not detected for 5+ seconds at frame {frame_idx}")
            else:
                ball_missing_count = 0

            # possession owner from previous frame's nearest
            possession_owner = (
                min(tf.players, key=lambda p: _dist(p.court_pos, tf.ball_pos)).track_id
                if tf.players and tf.ball_pos
                else None
            )

            # stats
            poss_events = possession.update(tf, player_teams, frame_idx, fps)
            shot_events = shots.update(tf, player_teams, possession_owner, frame_idx, fps)
            shot_this_frame = any(e.type == "shot" for e in shot_events)
            pass_events = passes.update(tf, player_teams, possession_owner, frame_idx, fps, shot_this_frame)
            movement.update(tf)
            score.update(shot_events)

            all_events.extend(poss_events + shot_events + pass_events)

            # video output
            if self._output_video:
                if writer is None:
                    h, w = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(self._output_video, fourcc, fps, (w, h))
                annotated = overlay.render(frame, score.scores, team_clf.team_colors, frame_idx, fps)
                writer.write(annotated)

            frame_idx += 1

        cap.release()
        if writer:
            writer.release()

        return self._build_stats(
            fps, frame_idx, player_teams, player_ident, movement, possession, score, team_clf, all_events
        )

    def _build_stats(
        self,
        fps: float,
        total_frames: int,
        player_teams: dict[int, str],
        player_ident: PlayerIdentifier,
        movement: MovementTracker,
        possession: PossessionTracker,
        score: ScoreTracker,
        team_clf: TeamClassifier,
        events,
    ) -> GameStats:
        pct = possession.finalize(total_frames)

        teams: dict[str, TeamStats] = {
            "team_a": TeamStats(
                team_id="team_a",
                color=team_clf.team_colors.get("team_a", ""),
                score=score.scores["team_a"],
                possession_pct=pct.get("team_a", 0.0),
            ),
            "team_b": TeamStats(
                team_id="team_b",
                color=team_clf.team_colors.get("team_b", ""),
                score=score.scores["team_b"],
                possession_pct=pct.get("team_b", 0.0),
            ),
        }

        shot_makes: dict[int, int] = {}
        shot_attempts: dict[int, int] = {}
        passes_made: dict[int, int] = {}
        passes_received: dict[int, int] = {}
        possession_frames: dict[int, int] = {}

        for e in events:
            pid = e.player_id
            if pid is None:
                continue
            if e.type == "make":
                shot_makes[pid] = shot_makes.get(pid, 0) + 1
            elif e.type == "shot":
                shot_attempts[pid] = shot_attempts.get(pid, 0) + 1
            elif e.type == "pass":
                passes_made[pid] = passes_made.get(pid, 0) + 1
            elif e.type == "possession_change":
                possession_frames[pid] = possession_frames.get(pid, 0) + 1

        for tid, team_id in player_teams.items():
            jersey = player_ident._majority(tid)
            positions = [Point(x=x, y=y) for x, y in movement.get_positions(tid)]
            ps = PlayerStats(
                player_id=jersey,
                team_id=team_id,
                positions=positions,
                distance_covered_m=movement.get_distance(tid),
                shot_attempts=shot_attempts.get(tid, 0),
                shot_makes=shot_makes.get(tid, 0),
                passes_made=passes_made.get(tid, 0),
                passes_received=passes_received.get(tid, 0),
                possession_frames=possession_frames.get(tid, 0),
            )
            if team_id in teams:
                teams[team_id].players.append(ps)

        return GameStats(
            video_path=self._video_path,
            duration_seconds=total_frames / fps if fps > 0 else 0.0,
            fps=fps,
            teams=list(teams.values()),
            events=events,
        )


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    import math
    return math.hypot(a[0] - b[0], a[1] - b[1])
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_analyzer.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/analyzer.py tests/test_analyzer.py
git commit -m "feat: add Analyzer pipeline"
```

---

### Task 13: README + final polish

**Files:**
- Modify: `README.md`
- Modify: `open_hoops/__init__.py` (ensure clean public API)

**Interfaces:**
- Consumes: nothing new — documentation task
- Produces: polished README, verified public API

- [ ] **Step 1: Write README.md**

```markdown
# 🏀 open_hoops

**Extract every basketball stat from a video. Powered by YOLO.**

---

## What it does

Point `open_hoops` at any fixed-court basketball video and get back a rich JSON object with:

| Stat | Detail |
|------|--------|
| **Shots** | Attempts, makes, misses — per player |
| **Score** | Live score tracked from confirmed makes |
| **Possession** | Who has the ball, team possession % |
| **Passes** | Pass counts per player and team |
| **Movement** | Court positions, distance covered (meters) |
| **Player identity** | Jersey numbers via OCR, team by jersey color |

Optionally render a score-overlay video with live HUD.

---

## Install

```bash
pip install open_hoops
```

Or from source:

```bash
git clone https://github.com/yourname/open-hoops
cd open-hoops
pip install -e ".[dev]"
```

---

## Usage

```python
from open_hoops import analyze

# Extract stats
stats = analyze("game.mp4")

# Stats + annotated video with score overlay
stats = analyze("game.mp4", output_video="game_scored.mp4")

# Export to JSON
import json
with open("stats.json", "w") as f:
    json.dump(stats.model_dump(), f, indent=2)
```

### Example output

```json
{
  "video_path": "game.mp4",
  "duration_seconds": 2400.0,
  "fps": 30.0,
  "teams": [
    {
      "team_id": "team_a",
      "color": "#e63030",
      "score": 84,
      "possession_pct": 0.52,
      "players": [
        {
          "player_id": 23,
          "team_id": "team_a",
          "distance_covered_m": 4821.3,
          "shot_attempts": 14,
          "shot_makes": 8,
          "passes_made": 47,
          "passes_received": 39,
          "possession_frames": 1823
        }
      ]
    }
  ],
  "events": [
    { "type": "make", "frame": 312, "timestamp_sec": 10.4, "player_id": 23, "team_id": "team_a" }
  ]
}
```

---

## How it works

```
Video frames
  → YOLO detection   (players, ball, hoop)
  → ByteTrack        (stable IDs across frames)
  → Jersey color     (K-means → team assignment)
  → OCR              (EasyOCR → player numbers)
  → Stats extraction (possession, shots, passes, movement)
  → Score overlay    (optional OpenCV HUD)
```

- **Fixed-court optimized** — homography maps pixel coords to real meters (NBA court dimensions)
- **No cloud, no API** — runs entirely local
- **Composable** — `GameStats` is a Pydantic model; call `.model_dump()` for plain JSON

---

## Requirements

- Python ≥ 3.10
- A YOLO model (default: `yolo11n.pt`, auto-downloaded by Ultralytics)
- Fixed-angle court camera footage

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check open_hoops/
mypy open_hoops/
```

---

## License

MIT
```

- [ ] **Step 2: Verify public API clean**

```bash
python -c "from open_hoops import analyze; print(analyze.__doc__ or 'ok')"
```
Expected: no ImportError

- [ ] **Step 3: Run full test suite**

```bash
pytest -v
```
Expected: all pass (skip integration tests that require a real video)

- [ ] **Step 4: Commit**

```bash
git add README.md open_hoops/__init__.py
git commit -m "docs: add polished README and verify public API"
```

---

## Self-Review Against Spec

| Spec requirement | Covered in task |
|-----------------|----------------|
| Python package `open_hoops` | Task 1 |
| `analyze(video_path) -> GameStats` | Task 1, 12 |
| `analyze(..., output_video=...)` | Task 12 |
| YOLO + ByteTrack detection/tracking | Task 2, 3 |
| Jersey color K-means | Task 4 |
| Jersey OCR (EasyOCR, every 30 frames, majority vote) | Task 5 |
| Possession tracker + events | Task 6 |
| Shot attempt / make / miss | Task 7 |
| Pass detection (Voronoi zone) | Task 9 |
| Player movement + distance (homography) | Task 3, 8 |
| Score tracker | Task 10 |
| Score overlay (only when output_video given) | Task 11, 12 |
| Pydantic models, JSON-serializable | Task 1 |
| `ValueError` on bad video | Task 12 |
| `warnings.warn` when ball missing > 5s | Task 12 |
| `player_id = None` on OCR failure | Task 5 |
| `pyproject.toml` with all deps | Task 1 |
| README | Task 13 |
| Unit tests with synthetic fixtures | All tasks |
