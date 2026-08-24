# Pipeline Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the YOLO-based video analysis pipeline with RF-DETR + SAM2 + SigLIP + SmolVLM2 + keypoint homography, matching the Roboflow notebook implementation.

**Architecture:** RF-DETR (10-class) detects players, ball, player states, and jersey number regions. SAM2 tracks players with persistent pixel-level masks. SigLIP+UMAP+KMeans clusters teams. SmolVLM2 reads jersey numbers from detected number crops. Keypoint model computes court homography automatically. Detection classes replace heuristic event detectors.

**Tech Stack:** `inference` (Roboflow), `sam2` (Meta real-time fork), `supervision>=0.27.0`, `sports` (Roboflow basketball branch), `transformers`, `umap-learn`, `torch`, `opencv-python`, `numpy`

**Spec:** `docs/superpowers/specs/2026-08-23-pipeline-upgrade-design.md`

## Global Constraints

- Python >=3.12
- Never use `from __future__ import annotations`
- All `__init__.py` files must be empty
- All imports at top of file
- Use string annotations for forward references
- API models use `uid: str(32)`, never expose internal `id`
- `AnalysisResult` remains the output contract between analyzer and worker

---

### Task 1: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: Updated dependency list that all subsequent tasks rely on

- [ ] **Step 1: Update pyproject.toml with new dependencies**

Replace the current dependencies block:

```toml
[project]
name = "open_hoops"
version = "0.2.0"
description = "Extract basketball stats from video using RF-DETR + SAM2"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = [
    "inference>=0.30",
    "supervision>=0.27.0",
    "sports @ git+https://github.com/roboflow/sports.git@feat/basketball",
    "torch>=2.0",
    "transformers>=4.40",
    "umap-learn>=0.5",
    "opencv-python>=4.9",
    "pydantic>=2.0",
    "numpy>=1.26",
    "sqlalchemy>=2.0",
]
```

Remove `ultralytics`, `easyocr`, `scikit-learn` from dependencies.

- [ ] **Step 2: Verify dependency resolution**

Run: `pip install -e ".[dev]"` (or `uv pip install -e ".[dev]"`)

Expected: All packages install without conflict.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: replace YOLO/easyocr deps with RF-DETR/SAM2/supervision stack"
```

---

### Task 2: RF-DETR Detection Module

**Files:**
- Create: `open_hoops/detection/__init__.py`
- Create: `open_hoops/detection/rfdetr.py`
- Create: `open_hoops/tests/test_detection_rfdetr.py`

**Interfaces:**
- Produces: `RFDETRDetector` class with method `detect(frame: np.ndarray) -> sv.Detections`. Constants `PLAYER_CLASS_IDS`, `NUMBER_CLASS_ID`, `BALL_CLASS_ID`, `BALL_IN_BASKET_CLASS_ID`, `PLAYER_JUMP_SHOT_CLASS_ID`, `PLAYER_LAYUP_DUNK_CLASS_ID`, `PLAYER_IN_POSSESSION_CLASS_ID`.

- [ ] **Step 1: Create empty `__init__.py`**

```python
# open_hoops/detection/__init__.py — must be empty per project conventions
```

- [ ] **Step 2: Write failing test**

```python
# open_hoops/tests/test_detection_rfdetr.py
from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from open_hoops.detection.rfdetr import (
    BALL_CLASS_ID,
    BALL_IN_BASKET_CLASS_ID,
    NUMBER_CLASS_ID,
    PLAYER_CLASS_IDS,
    PLAYER_IN_POSSESSION_CLASS_ID,
    PLAYER_JUMP_SHOT_CLASS_ID,
    PLAYER_LAYUP_DUNK_CLASS_ID,
    RFDETRDetector,
)


def _mock_inference_result():
    """Create a mock inference result mimicking Roboflow API response."""
    mock_result = MagicMock()
    mock_result.xyxy = np.array([[100, 200, 150, 300], [400, 200, 450, 300]])
    mock_result.confidence = np.array([0.9, 0.85])
    mock_result.class_id = np.array([3, 4])
    mock_result.data = {}
    return mock_result


@patch("open_hoops.detection.rfdetr.get_model")
def test_detect_returns_supervision_detections(mock_get_model):
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_model.infer.return_value = [_mock_inference_result()]

    with patch("supervision.Detections.from_inference") as mock_from_inf:
        mock_from_inf.return_value = sv.Detections(
            xyxy=np.array([[100, 200, 150, 300], [400, 200, 450, 300]]),
            confidence=np.array([0.9, 0.85]),
            class_id=np.array([3, 4]),
        )
        detector = RFDETRDetector()
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = detector.detect(frame)

    assert isinstance(result, sv.Detections)
    assert len(result) == 2


@patch("open_hoops.detection.rfdetr.get_model")
def test_filter_players(mock_get_model):
    mock_get_model.return_value = MagicMock()

    detector = RFDETRDetector()
    detections = sv.Detections(
        xyxy=np.array([[0, 0, 1, 1]] * 4),
        confidence=np.array([0.9, 0.9, 0.9, 0.9]),
        class_id=np.array([3, 4, 5, 8]),  # player, possession, jump-shot, referee
    )
    players = detector.filter_players(detections)
    assert len(players) == 3  # referee excluded


@patch("open_hoops.detection.rfdetr.get_model")
def test_filter_numbers(mock_get_model):
    mock_get_model.return_value = MagicMock()

    detector = RFDETRDetector()
    detections = sv.Detections(
        xyxy=np.array([[0, 0, 1, 1]] * 3),
        confidence=np.array([0.9, 0.9, 0.9]),
        class_id=np.array([2, 3, 4]),  # number, player, possession
    )
    numbers = detector.filter_numbers(detections)
    assert len(numbers) == 1


def test_class_id_constants():
    assert BALL_CLASS_ID == 0
    assert BALL_IN_BASKET_CLASS_ID == 1
    assert NUMBER_CLASS_ID == 2
    assert 3 in PLAYER_CLASS_IDS
    assert 4 in PLAYER_CLASS_IDS  # player-in-possession
    assert 5 in PLAYER_CLASS_IDS  # player-jump-shot
    assert 6 in PLAYER_CLASS_IDS  # player-layup-dunk
    assert 7 in PLAYER_CLASS_IDS  # player-shot-block
    assert PLAYER_IN_POSSESSION_CLASS_ID == 4
    assert PLAYER_JUMP_SHOT_CLASS_ID == 5
    assert PLAYER_LAYUP_DUNK_CLASS_ID == 6
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest open_hoops/tests/test_detection_rfdetr.py -v`
Expected: FAIL (module not found)

- [ ] **Step 4: Implement RFDETRDetector**

```python
# open_hoops/detection/rfdetr.py
import numpy as np
import supervision as sv
from inference import get_model

BALL_CLASS_ID = 0
BALL_IN_BASKET_CLASS_ID = 1
NUMBER_CLASS_ID = 2
PLAYER_IN_POSSESSION_CLASS_ID = 4
PLAYER_JUMP_SHOT_CLASS_ID = 5
PLAYER_LAYUP_DUNK_CLASS_ID = 6
PLAYER_SHOT_BLOCK_CLASS_ID = 7
PLAYER_CLASS_IDS = [3, 4, 5, 6, 7]

MODEL_ID = "basketball-player-detection-3-ycjdo/4"
DEFAULT_CONFIDENCE = 0.4
DEFAULT_IOU_THRESHOLD = 0.9


class RFDETRDetector:
    def __init__(
        self,
        model_id: str = MODEL_ID,
        confidence: float = DEFAULT_CONFIDENCE,
        iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    ) -> None:
        self._model = get_model(model_id=model_id)
        self._confidence = confidence
        self._iou_threshold = iou_threshold

    def detect(self, frame: np.ndarray) -> sv.Detections:
        result = self._model.infer(
            frame,
            confidence=self._confidence,
            iou_threshold=self._iou_threshold,
        )[0]
        return sv.Detections.from_inference(result)

    def filter_players(self, detections: sv.Detections) -> sv.Detections:
        return detections[np.isin(detections.class_id, PLAYER_CLASS_IDS)]

    def filter_numbers(self, detections: sv.Detections) -> sv.Detections:
        return detections[detections.class_id == NUMBER_CLASS_ID]

    def filter_ball(self, detections: sv.Detections) -> sv.Detections:
        return detections[detections.class_id == BALL_CLASS_ID]
```

- [ ] **Step 5: Run tests**

Run: `pytest open_hoops/tests/test_detection_rfdetr.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add open_hoops/detection/ open_hoops/tests/test_detection_rfdetr.py
git commit -m "feat: add RF-DETR detection module (10-class basketball model)"
```

---

### Task 3: SAM2 Tracker Module

**Files:**
- Create: `open_hoops/tracking/__init__.py`
- Create: `open_hoops/tracking/sam2_tracker.py`
- Create: `open_hoops/tests/test_tracking_sam2.py`

**Interfaces:**
- Consumes: `sv.Detections` from Task 2
- Produces: `SAM2Tracker` class with methods `prompt_first_frame(frame, detections)`, `track_frame(frame) -> sv.Detections` (with masks and tracker_id). `TrackedFrame` dataclass with `players: list[TrackedPlayer]`, `ball_pos`, `frame_idx`.

- [ ] **Step 1: Create empty `__init__.py`**

- [ ] **Step 2: Write failing test**

```python
# open_hoops/tests/test_tracking_sam2.py
from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from open_hoops.tracking.sam2_tracker import SAM2Tracker, TrackedFrame, TrackedPlayer


@patch("open_hoops.tracking.sam2_tracker.build_sam2_camera_predictor")
def test_prompt_first_frame(mock_build):
    mock_predictor = MagicMock()
    mock_build.return_value = mock_predictor

    tracker = SAM2Tracker()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detections = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300], [400, 200, 450, 300]]),
        confidence=np.array([0.9, 0.85]),
        class_id=np.array([3, 3]),
        tracker_id=np.array([1, 2]),
    )
    tracker.prompt_first_frame(frame, detections)

    mock_predictor.load_first_frame.assert_called_once()
    assert mock_predictor.add_new_prompt.call_count == 2


@patch("open_hoops.tracking.sam2_tracker.build_sam2_camera_predictor")
def test_track_frame_returns_detections_with_masks(mock_build):
    mock_predictor = MagicMock()
    mock_build.return_value = mock_predictor

    # Simulate SAM2 output: dict of obj_id -> mask
    mask1 = np.zeros((720, 1280), dtype=bool)
    mask1[200:300, 100:150] = True
    mask2 = np.zeros((720, 1280), dtype=bool)
    mask2[200:300, 400:450] = True
    mock_predictor.track.return_value = ({1: mask1, 2: mask2}, {1: 0.95, 2: 0.9})

    tracker = SAM2Tracker()
    tracker._predictor = mock_predictor
    tracker._prompted = True

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = tracker.track_frame(frame)

    assert isinstance(result, sv.Detections)
    assert len(result) == 2
    assert result.tracker_id is not None
    assert result.mask is not None


def test_tracked_frame_dataclass():
    player = TrackedPlayer(track_id=1, bbox=(100, 200, 150, 300), court_pos=(5.0, 7.0))
    tf = TrackedFrame(players=[player], ball_pos=(10.0, 5.0), frame_idx=42)
    assert tf.players[0].track_id == 1
    assert tf.ball_pos == (10.0, 5.0)
    assert tf.frame_idx == 42
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest open_hoops/tests/test_tracking_sam2.py -v`
Expected: FAIL

- [ ] **Step 4: Implement SAM2Tracker**

```python
# open_hoops/tracking/sam2_tracker.py
from dataclasses import dataclass, field

import numpy as np
import supervision as sv
import torch
from sam2.build_sam import build_sam2_camera_predictor

SAM2_CHECKPOINT = "checkpoints/sam2.1_hiera_large.pt"
SAM2_CONFIG = "configs/sam2.1/sam2.1_hiera_l.yaml"


@dataclass
class TrackedPlayer:
    track_id: int
    bbox: tuple[int, int, int, int]
    court_pos: tuple[float, float] = (0.0, 0.0)
    mask: np.ndarray | None = None


@dataclass
class TrackedFrame:
    players: list[TrackedPlayer] = field(default_factory=list)
    ball_pos: tuple[float, float] | None = None
    frame_idx: int = 0


class SAM2Tracker:
    def __init__(
        self,
        checkpoint: str = SAM2_CHECKPOINT,
        config: str = SAM2_CONFIG,
    ) -> None:
        self._predictor = build_sam2_camera_predictor(config, checkpoint)
        self._prompted = False

    def prompt_first_frame(self, frame: np.ndarray, detections: sv.Detections) -> None:
        if len(detections) == 0:
            return
        if detections.tracker_id is None:
            detections.tracker_id = np.arange(1, len(detections) + 1)

        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            self._predictor.load_first_frame(frame)
            for xyxy, obj_id in zip(detections.xyxy, detections.tracker_id):
                bbox = np.asarray([xyxy], dtype=np.float32)
                self._predictor.add_new_prompt(
                    frame_idx=0,
                    obj_id=int(obj_id),
                    bbox=bbox,
                )
        self._prompted = True

    def track_frame(self, frame: np.ndarray) -> sv.Detections:
        if not self._prompted:
            return sv.Detections.empty()

        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            obj_ids, masks = self._predictor.track(frame)

        if len(obj_ids) == 0:
            return sv.Detections.empty()

        mask_array = masks.cpu().numpy().astype(bool)
        xyxy = sv.mask_to_xyxy(mask_array)

        return sv.Detections(
            xyxy=xyxy,
            mask=mask_array,
            tracker_id=np.array(obj_ids, dtype=int),
        )

    def add_new_object(self, frame: np.ndarray, bbox: np.ndarray, obj_id: int) -> None:
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            self._predictor.add_new_prompt(
                frame_idx=0,
                obj_id=obj_id,
                bbox=np.asarray([bbox], dtype=np.float32),
            )
```

- [ ] **Step 5: Run tests**

Run: `pytest open_hoops/tests/test_tracking_sam2.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add open_hoops/tracking/ open_hoops/tests/test_tracking_sam2.py
git commit -m "feat: add SAM2 tracking module with pixel-level masks"
```

---

### Task 4: Team Classification Module

**Files:**
- Create: `open_hoops/identity/__init__.py` (already exists, ensure empty)
- Create: `open_hoops/identity/team_classifier.py`
- Create: `open_hoops/tests/test_team_classifier.py`

**Interfaces:**
- Consumes: Player crops (numpy arrays) from SAM2 masks
- Produces: `TeamClassifierWrapper` class with `fit(crops: list[np.ndarray])`, `predict(crop: np.ndarray) -> int` (0 or 1). Dict `TEAM_NAMES` mapping cluster ID to team label.

- [ ] **Step 1: Write failing test**

```python
# open_hoops/tests/test_team_classifier.py
from unittest.mock import MagicMock, patch

import numpy as np

from open_hoops.identity.team_classifier import TeamClassifierWrapper


@patch("open_hoops.identity.team_classifier.TeamClassifier")
def test_fit_calls_underlying_classifier(mock_tc_class):
    mock_tc = MagicMock()
    mock_tc_class.return_value = mock_tc

    wrapper = TeamClassifierWrapper(device="cpu")
    crops = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(10)]
    wrapper.fit(crops)

    mock_tc.fit.assert_called_once_with(crops)


@patch("open_hoops.identity.team_classifier.TeamClassifier")
def test_predict_returns_team_id(mock_tc_class):
    mock_tc = MagicMock()
    mock_tc_class.return_value = mock_tc
    mock_tc.predict.return_value = 0

    wrapper = TeamClassifierWrapper(device="cpu")
    crop = np.zeros((64, 64, 3), dtype=np.uint8)
    result = wrapper.predict(crop)

    assert result in (0, 1)


@patch("open_hoops.identity.team_classifier.TeamClassifier")
def test_predict_batch(mock_tc_class):
    mock_tc = MagicMock()
    mock_tc_class.return_value = mock_tc
    mock_tc.predict.side_effect = [0, 1, 0]

    wrapper = TeamClassifierWrapper(device="cpu")
    crops = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(3)]
    results = wrapper.predict_batch(crops)

    assert results == [0, 1, 0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest open_hoops/tests/test_team_classifier.py -v`
Expected: FAIL

- [ ] **Step 3: Implement TeamClassifierWrapper**

```python
# open_hoops/identity/team_classifier.py
import numpy as np
from sports import TeamClassifier


class TeamClassifierWrapper:
    def __init__(self, device: str = "cuda") -> None:
        self._classifier = TeamClassifier(device=device)

    def fit(self, crops: list[np.ndarray]) -> None:
        self._classifier.fit(crops)

    def predict(self, crop: np.ndarray) -> int:
        return self._classifier.predict(crop)

    def predict_batch(self, crops: list[np.ndarray]) -> list[int]:
        return [self._classifier.predict(crop) for crop in crops]
```

- [ ] **Step 4: Run tests**

Run: `pytest open_hoops/tests/test_team_classifier.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add open_hoops/identity/team_classifier.py open_hoops/tests/test_team_classifier.py
git commit -m "feat: add SigLIP+UMAP+KMeans team classifier via sports lib"
```

---

### Task 5: Jersey Number Reader Module

**Files:**
- Create: `open_hoops/identity/number_reader.py`
- Create: `open_hoops/tests/test_number_reader.py`

**Interfaces:**
- Consumes: `sv.Detections` (number class filtered), frame (numpy array)
- Produces: `NumberReader` class with `read(frame, number_detections) -> dict[int, str | None]` mapping detection index to recognized number string. `NumberValidator` class with `update(track_id, number) -> int | None` returning locked number or None.

- [ ] **Step 1: Write failing test**

```python
# open_hoops/tests/test_number_reader.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest open_hoops/tests/test_number_reader.py -v`
Expected: FAIL

- [ ] **Step 3: Implement NumberReader and NumberValidator**

```python
# open_hoops/identity/number_reader.py
import numpy as np
import supervision as sv
from inference import get_model

NUMBER_MODEL_ID = "basketball-jersey-numbers-ocr/3"
NUMBER_PROMPT = "Read the number."
CROP_PAD = 10


class NumberReader:
    def __init__(self, model_id: str = NUMBER_MODEL_ID) -> None:
        self._model = get_model(model_id=model_id)

    def read(self, frame: np.ndarray, detections: sv.Detections) -> dict[int, str | None]:
        results: dict[int, str | None] = {}
        h, w = frame.shape[:2]

        for idx, xyxy in enumerate(detections.xyxy):
            x1 = max(0, int(xyxy[0]) - CROP_PAD)
            y1 = max(0, int(xyxy[1]) - CROP_PAD)
            x2 = min(w, int(xyxy[2]) + CROP_PAD)
            y2 = min(h, int(xyxy[3]) + CROP_PAD)
            crop = frame[y1:y2, x1:x2]

            if crop.size == 0:
                results[idx] = None
                continue

            response = self._model.infer(crop, prompt=NUMBER_PROMPT)
            results[idx] = response.output if response.output else None

        return results


class NumberValidator:
    def __init__(self, threshold: int = 3) -> None:
        self._threshold = threshold
        self._streaks: dict[int, tuple[str, int]] = {}
        self._locked: dict[int, int] = {}

    def update(self, track_id: int, number_str: str | None) -> int | None:
        if track_id in self._locked:
            return self._locked[track_id]

        if number_str is None or not number_str.strip().isdigit():
            return None

        current = self._streaks.get(track_id)
        if current and current[0] == number_str:
            count = current[1] + 1
            self._streaks[track_id] = (number_str, count)
            if count >= self._threshold:
                self._locked[track_id] = int(number_str)
                return self._locked[track_id]
        else:
            self._streaks[track_id] = (number_str, 1)

        return None
```

- [ ] **Step 4: Run tests**

Run: `pytest open_hoops/tests/test_number_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add open_hoops/identity/number_reader.py open_hoops/tests/test_number_reader.py
git commit -m "feat: add two-stage jersey number reader (RF-DETR + SmolVLM2 + validation)"
```

---

### Task 6: Court Keypoint Homography Module

**Files:**
- Create: `open_hoops/court/__init__.py`
- Create: `open_hoops/court/keypoint_homography.py`
- Create: `open_hoops/tests/test_court_homography.py`

**Interfaces:**
- Consumes: Video frames (numpy arrays)
- Produces: `CourtMapper` class with `detect_keypoints(frame) -> np.ndarray`, `compute_homography(frame) -> np.ndarray | None`, `pixel_to_court(points: np.ndarray) -> np.ndarray`. Uses `sports.ViewTransformer` and `sports.basketball.CourtConfiguration`.

- [ ] **Step 1: Create empty `__init__.py`**

- [ ] **Step 2: Write failing test**

```python
# open_hoops/tests/test_court_homography.py
from unittest.mock import MagicMock, patch

import numpy as np

from open_hoops.court.keypoint_homography import CourtMapper


@patch("open_hoops.court.keypoint_homography.get_model")
def test_detect_keypoints_returns_array(mock_get_model):
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model

    mock_result = MagicMock()
    mock_result.keypoints = MagicMock()
    mock_result.keypoints.xy = np.array([[[100.0, 200.0], [300.0, 400.0], [500.0, 600.0]]])
    mock_result.keypoints.confidence = np.array([[0.9, 0.6, 0.3]])
    mock_model.infer.return_value = [mock_result]

    mapper = CourtMapper(anchor_confidence=0.5)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    keypoints = mapper.detect_keypoints(frame)

    # Only keypoints above anchor_confidence (0.5) returned
    assert keypoints.shape[0] == 2  # 0.9 and 0.6, not 0.3


def test_pixel_to_court_with_known_homography():
    mapper = CourtMapper.__new__(CourtMapper)
    # Identity-like homography for simple test
    mapper._view_transformer = MagicMock()
    mapper._view_transformer.transform_points.return_value = np.array([[14.0, 7.5]])

    points = np.array([[640, 360]])
    result = mapper.pixel_to_court(points)
    assert result.shape == (1, 2)
    assert result[0, 0] == 14.0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest open_hoops/tests/test_court_homography.py -v`
Expected: FAIL

- [ ] **Step 4: Implement CourtMapper**

```python
# open_hoops/court/keypoint_homography.py
import numpy as np
from inference import get_model
from sports import ViewTransformer
from sports.basketball import CourtConfiguration, League

KEYPOINT_MODEL_ID = "basketball-court-detection-2/14"
DEFAULT_CONFIDENCE = 0.3
DEFAULT_ANCHOR_CONFIDENCE = 0.5


class CourtMapper:
    def __init__(
        self,
        model_id: str = KEYPOINT_MODEL_ID,
        confidence: float = DEFAULT_CONFIDENCE,
        anchor_confidence: float = DEFAULT_ANCHOR_CONFIDENCE,
        league: League = League.NBA,
    ) -> None:
        self._model = get_model(model_id=model_id)
        self._confidence = confidence
        self._anchor_confidence = anchor_confidence
        self._court_config = CourtConfiguration(league=league)
        self._view_transformer: ViewTransformer | None = None

    def detect_keypoints(self, frame: np.ndarray) -> np.ndarray:
        result = self._model.infer(frame, confidence=self._confidence)[0]
        xy = result.keypoints.xy[0]
        conf = result.keypoints.confidence[0]
        mask = conf >= self._anchor_confidence
        return xy[mask]

    def compute_homography(self, frame: np.ndarray) -> bool:
        keypoints = self.detect_keypoints(frame)
        if len(keypoints) < 4:
            return False

        court_points = self._court_config.get_court_points(keypoints)
        self._view_transformer = ViewTransformer(
            source=keypoints,
            target=court_points,
        )
        return True

    def pixel_to_court(self, points: np.ndarray) -> np.ndarray:
        if self._view_transformer is None:
            return points
        return self._view_transformer.transform_points(points)
```

- [ ] **Step 5: Run tests**

Run: `pytest open_hoops/tests/test_court_homography.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add open_hoops/court/ open_hoops/tests/test_court_homography.py
git commit -m "feat: add court keypoint detection and automatic homography"
```

---

### Task 7: Event Detector Module (Detection-Based)

**Files:**
- Create: `open_hoops/stats/event_detector.py`
- Create: `open_hoops/tests/test_event_detector.py`

**Interfaces:**
- Consumes: `sv.Detections` from RF-DETR (full detections per frame), player team assignments `dict[int, str]`, frame index, fps
- Produces: `EventDetector` class with `update(detections, tracker_detections, team_assignments, frame_idx, fps) -> list[AnalyzedEvent]`. Detects shots, makes, possession changes from detection classes.

- [ ] **Step 1: Write failing test**

```python
# open_hoops/tests/test_event_detector.py
import numpy as np
import supervision as sv

from open_hoops.stats.event_detector import EventDetector


def _make_detections(class_ids, tracker_ids=None):
    n = len(class_ids)
    return sv.Detections(
        xyxy=np.array([[0, 0, 1, 1]] * n),
        confidence=np.array([0.9] * n),
        class_id=np.array(class_ids),
        tracker_id=np.array(tracker_ids) if tracker_ids else None,
    )


def test_detects_jump_shot_event():
    detector = EventDetector()
    teams = {1: "team_a"}
    detections = _make_detections([5], tracker_ids=[1])  # player-jump-shot
    events = detector.update(detections, teams, frame_idx=10, fps=30.0)
    shot_events = [e for e in events if e.type == "shot"]
    assert len(shot_events) == 1
    assert shot_events[0].team_id == "team_a"


def test_detects_make_from_ball_in_basket():
    detector = EventDetector()
    teams = {1: "team_a"}
    # First: shot attempt
    detector.update(_make_detections([5], tracker_ids=[1]), teams, frame_idx=10, fps=30.0)
    # Then: ball in basket
    events = detector.update(_make_detections([1]), teams, frame_idx=15, fps=30.0)
    make_events = [e for e in events if e.type == "make"]
    assert len(make_events) == 1


def test_detects_possession_from_class():
    detector = EventDetector()
    teams = {1: "team_a", 2: "team_b"}
    # Player 1 has possession
    detector.update(_make_detections([4], tracker_ids=[1]), teams, frame_idx=0, fps=30.0)
    # Player 2 has possession (team change)
    events = detector.update(_make_detections([4], tracker_ids=[2]), teams, frame_idx=5, fps=30.0)
    poss_events = [e for e in events if e.type == "possession_change"]
    assert len(poss_events) == 1
    assert poss_events[0].team_id == "team_b"


def test_no_duplicate_shot_same_sequence():
    detector = EventDetector()
    teams = {1: "team_a"}
    detector.update(_make_detections([5], tracker_ids=[1]), teams, frame_idx=10, fps=30.0)
    # Same shot continuing next frame should not fire again
    events = detector.update(_make_detections([5], tracker_ids=[1]), teams, frame_idx=11, fps=30.0)
    shot_events = [e for e in events if e.type == "shot"]
    assert len(shot_events) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest open_hoops/tests/test_event_detector.py -v`
Expected: FAIL

- [ ] **Step 3: Implement EventDetector**

```python
# open_hoops/stats/event_detector.py
import numpy as np
import supervision as sv

from open_hoops.detection.rfdetr import (
    BALL_IN_BASKET_CLASS_ID,
    PLAYER_IN_POSSESSION_CLASS_ID,
    PLAYER_JUMP_SHOT_CLASS_ID,
    PLAYER_LAYUP_DUNK_CLASS_ID,
)
from open_hoops.service.analysis.models import AnalyzedEvent

SHOT_CLASS_IDS = [PLAYER_JUMP_SHOT_CLASS_ID, PLAYER_LAYUP_DUNK_CLASS_ID]
SHOT_COOLDOWN_FRAMES = 15


class EventDetector:
    def __init__(self) -> None:
        self._current_possession_team: str | None = None
        self._current_possession_player: int | None = None
        self._last_shot_frame: int = -999
        self._awaiting_make: bool = False
        self._last_shooter: int | None = None
        self._last_shooter_team: str | None = None

    def update(
        self,
        detections: sv.Detections,
        team_assignments: dict[int, str],
        frame_idx: int,
        fps: float,
    ) -> list[AnalyzedEvent]:
        events: list[AnalyzedEvent] = []
        timestamp = frame_idx / fps

        # Possession detection
        poss_mask = detections.class_id == PLAYER_IN_POSSESSION_CLASS_ID
        if poss_mask.any() and detections.tracker_id is not None:
            poss_ids = detections.tracker_id[poss_mask]
            player_id = int(poss_ids[0])
            team = team_assignments.get(player_id)
            if team and team != self._current_possession_team:
                events.append(AnalyzedEvent(
                    type="possession_change",
                    frame=frame_idx,
                    timestamp_sec=timestamp,
                    player_id=player_id,
                    team_id=team,
                ))
            self._current_possession_team = team
            self._current_possession_player = player_id

        # Shot detection
        shot_mask = np.isin(detections.class_id, SHOT_CLASS_IDS)
        if shot_mask.any() and (frame_idx - self._last_shot_frame) > SHOT_COOLDOWN_FRAMES:
            shooter_id = None
            if detections.tracker_id is not None:
                shot_tracker_ids = detections.tracker_id[shot_mask]
                shooter_id = int(shot_tracker_ids[0])

            team = team_assignments.get(shooter_id) if shooter_id else self._current_possession_team
            events.append(AnalyzedEvent(
                type="shot",
                frame=frame_idx,
                timestamp_sec=timestamp,
                player_id=shooter_id,
                team_id=team,
            ))
            self._last_shot_frame = frame_idx
            self._awaiting_make = True
            self._last_shooter = shooter_id
            self._last_shooter_team = team

        # Make detection (ball-in-basket)
        make_mask = detections.class_id == BALL_IN_BASKET_CLASS_ID
        if make_mask.any() and self._awaiting_make:
            events.append(AnalyzedEvent(
                type="make",
                frame=frame_idx,
                timestamp_sec=timestamp,
                player_id=self._last_shooter,
                team_id=self._last_shooter_team,
            ))
            self._awaiting_make = False

        return events
```

- [ ] **Step 4: Run tests**

Run: `pytest open_hoops/tests/test_event_detector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add open_hoops/stats/event_detector.py open_hoops/tests/test_event_detector.py
git commit -m "feat: add detection-based event detector (shots, makes, possession)"
```

---

### Task 8: Rewrite Analyzer (Pipeline Orchestration)

**Files:**
- Rewrite: `open_hoops/analyzer.py`
- Create: `open_hoops/tests/test_analyzer_new.py`

**Interfaces:**
- Consumes: All modules from Tasks 2-7
- Produces: `OpenHoop` class with `extract_stats(video_path, roster) -> AnalysisResult`. Same `AnalysisResult` contract as before (worker unchanged).

- [ ] **Step 1: Write integration test**

```python
# open_hoops/tests/test_analyzer_new.py
from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from open_hoops.service.analysis.models import AnalysisResult, Roster, TeamRoster, Video


@patch("open_hoops.analyzer.CourtMapper")
@patch("open_hoops.analyzer.NumberReader")
@patch("open_hoops.analyzer.NumberValidator")
@patch("open_hoops.analyzer.TeamClassifierWrapper")
@patch("open_hoops.analyzer.SAM2Tracker")
@patch("open_hoops.analyzer.RFDETRDetector")
@patch("open_hoops.analyzer.sv.get_video_frames_generator")
def test_extract_stats_returns_analysis_result(
    mock_frames_gen, mock_detector_cls, mock_tracker_cls,
    mock_team_cls, mock_validator_cls, mock_reader_cls, mock_court_cls,
):
    # Setup: 3 frames of video
    frames = [np.zeros((720, 1280, 3), dtype=np.uint8) for _ in range(3)]
    mock_frames_gen.return_value = iter(frames)

    # Mock detector
    mock_detector = MagicMock()
    mock_detector_cls.return_value = mock_detector
    mock_detector.detect.return_value = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300]]),
        confidence=np.array([0.9]),
        class_id=np.array([3]),
    )
    mock_detector.filter_players.return_value = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300]]),
        confidence=np.array([0.9]),
        class_id=np.array([3]),
        tracker_id=np.array([1]),
    )
    mock_detector.filter_numbers.return_value = sv.Detections.empty()
    mock_detector.filter_ball.return_value = sv.Detections.empty()

    # Mock tracker
    mock_tracker = MagicMock()
    mock_tracker_cls.return_value = mock_tracker
    mock_tracker.track_frame.return_value = sv.Detections(
        xyxy=np.array([[100, 200, 150, 300]]),
        confidence=np.array([0.9]),
        class_id=np.array([3]),
        tracker_id=np.array([1]),
        mask=np.zeros((1, 720, 1280), dtype=bool),
    )

    # Mock team classifier
    mock_team = MagicMock()
    mock_team_cls.return_value = mock_team
    mock_team.predict.return_value = 0

    # Mock court mapper
    mock_court = MagicMock()
    mock_court_cls.return_value = mock_court
    mock_court.compute_homography.return_value = True
    mock_court.pixel_to_court.return_value = np.array([[14.0, 7.5]])

    # Mock number reader/validator
    mock_reader = MagicMock()
    mock_reader_cls.return_value = mock_reader
    mock_reader.read.return_value = {}
    mock_validator = MagicMock()
    mock_validator_cls.return_value = mock_validator

    from open_hoops.analyzer import OpenHoop

    roster = Roster(
        home=TeamRoster(color="#FF0000", players=[23]),
        away=TeamRoster(color="#0000FF", players=[7]),
    )
    oh = OpenHoop(Video(path="test.mp4"), roster=roster)
    result = oh.extract_stats()

    assert isinstance(result, AnalysisResult)
    assert result.fps > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest open_hoops/tests/test_analyzer_new.py -v`
Expected: FAIL

- [ ] **Step 3: Rewrite analyzer.py**

```python
# open_hoops/analyzer.py
import numpy as np
import supervision as sv

from open_hoops.court.keypoint_homography import CourtMapper
from open_hoops.detection.rfdetr import RFDETRDetector
from open_hoops.identity.number_reader import NumberReader, NumberValidator
from open_hoops.identity.team_classifier import TeamClassifierWrapper
from open_hoops.service.analysis.models import (
    AnalysisResult,
    AnalyzedEvent,
    AnalyzedPlayerStats,
    AnalyzedTeamStats,
    Point,
    Roster,
    Video,
)
from open_hoops.stats.event_detector import EventDetector
from open_hoops.stats.movement import MovementTracker
from open_hoops.stats.passes import PassDetector
from open_hoops.stats.score import ScoreTracker
from open_hoops.tracking.sam2_tracker import SAM2Tracker, TrackedFrame, TrackedPlayer

TEAM_SAMPLE_FPS = 1
NUMBER_READ_INTERVAL = 10


class OpenHoop:
    def __init__(
        self,
        video: "Video",
        roster: "Roster | None" = None,
    ) -> None:
        self._video = video
        self._roster = roster

    def extract_stats(self) -> "AnalysisResult":
        detector = RFDETRDetector()
        tracker = SAM2Tracker()
        court_mapper = CourtMapper()
        team_classifier = TeamClassifierWrapper()
        number_reader = NumberReader()
        number_validator = NumberValidator()
        event_detector = EventDetector()
        movement = MovementTracker()
        passes = PassDetector()
        score = ScoreTracker()

        frames = list(sv.get_video_frames_generator(self._video.path))
        fps = sv.VideoInfo.from_video_path(self._video.path).fps
        total_frames = len(frames)

        if total_frames == 0:
            return self._empty_result(fps)

        # Phase 1: Detect first frame, prompt SAM2
        first_detections = detector.detect(frames[0])
        player_detections = detector.filter_players(first_detections)
        player_detections.tracker_id = np.arange(1, len(player_detections) + 1)
        tracker.prompt_first_frame(frames[0], player_detections)

        # Phase 2: Compute court homography from first frame
        court_mapper.compute_homography(frames[0])

        # Phase 3: Collect team crops at 1 FPS for classifier training
        team_crops = self._collect_team_crops(frames, detector, tracker, fps)
        if team_crops:
            team_classifier.fit(team_crops)

        # Phase 4: Process all frames
        team_assignments: dict[int, str] = {}
        jersey_assignments: dict[int, int | None] = {}
        all_events: list[AnalyzedEvent] = []
        tracked_frames: list[TrackedFrame] = []

        for frame_idx, frame in enumerate(frames):
            # Detection
            detections = detector.detect(frame)

            # Tracking
            if frame_idx == 0:
                tracked = player_detections
            else:
                tracked = tracker.track_frame(frame)

            # Court mapping
            if tracked.tracker_id is not None and len(tracked) > 0:
                centers = np.array([
                    [(xyxy[0] + xyxy[2]) / 2, (xyxy[1] + xyxy[3]) / 2]
                    for xyxy in tracked.xyxy
                ])
                court_positions = court_mapper.pixel_to_court(centers)
            else:
                court_positions = np.empty((0, 2))

            # Build TrackedFrame
            tf = TrackedFrame(frame_idx=frame_idx)
            if tracked.tracker_id is not None:
                for i, tid in enumerate(tracked.tracker_id):
                    tid_int = int(tid)
                    court_pos = (float(court_positions[i, 0]), float(court_positions[i, 1]))
                    bbox = tuple(int(v) for v in tracked.xyxy[i])
                    tf.players.append(TrackedPlayer(
                        track_id=tid_int, bbox=bbox, court_pos=court_pos,
                    ))

            tracked_frames.append(tf)

            # Team assignment (once per player)
            if tracked.tracker_id is not None and tracked.mask is not None:
                for i, tid in enumerate(tracked.tracker_id):
                    tid_int = int(tid)
                    if tid_int not in team_assignments:
                        mask = tracked.mask[i]
                        crop = self._crop_from_mask(frame, mask, tracked.xyxy[i])
                        if crop is not None:
                            cluster = team_classifier.predict(crop)
                            team_assignments[tid_int] = "team_a" if cluster == 0 else "team_b"

            # Number reading
            if frame_idx % NUMBER_READ_INTERVAL == 0:
                number_dets = detector.filter_numbers(detections)
                if len(number_dets) > 0:
                    readings = number_reader.read(frame, number_dets)
                    self._match_numbers_to_players(
                        readings, number_dets, tracked, number_validator, jersey_assignments
                    )

            # Event detection
            frame_events = event_detector.update(detections, team_assignments, frame_idx, fps)

            # Pass detection (still proximity-based with better data)
            ball_dets = detector.filter_ball(detections)
            ball_pos = None
            if len(ball_dets) > 0:
                ball_center = np.array([
                    [(ball_dets.xyxy[0][0] + ball_dets.xyxy[0][2]) / 2,
                     (ball_dets.xyxy[0][1] + ball_dets.xyxy[0][3]) / 2]
                ])
                ball_court = court_mapper.pixel_to_court(ball_center)
                ball_pos = (float(ball_court[0, 0]), float(ball_court[0, 1]))
                tf.ball_pos = ball_pos

            shot_this_frame = any(e.type == "shot" for e in frame_events)
            possession_owner = None
            if tf.players and ball_pos:
                from math import hypot
                nearest = min(tf.players, key=lambda p: hypot(
                    p.court_pos[0] - ball_pos[0], p.court_pos[1] - ball_pos[1]
                ))
                possession_owner = nearest.track_id

            pass_events = passes.update(
                tf, team_assignments, possession_owner, frame_idx, fps, shot_this_frame
            )

            # Movement
            movement.update(tf)

            # Score
            score.update(frame_events)

            all_events.extend(frame_events + pass_events)

        return self._build_result(
            fps, total_frames, team_assignments, jersey_assignments,
            movement, score, all_events, tracked_frames,
        )

    def _collect_team_crops(
        self, frames, detector, tracker, fps,
    ) -> list[np.ndarray]:
        crops = []
        interval = max(1, int(fps / TEAM_SAMPLE_FPS))
        for i in range(0, min(len(frames), int(fps * 10)), interval):
            frame = frames[i]
            detections = detector.detect(frame)
            players = detector.filter_players(detections)
            for xyxy in players.xyxy:
                crop = self._central_crop(frame, xyxy)
                if crop is not None:
                    crops.append(crop)
        return crops

    def _central_crop(self, frame: np.ndarray, xyxy: np.ndarray) -> np.ndarray | None:
        x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
        h = y2 - y1
        cy1 = y1 + h // 4
        cy2 = y2 - h // 4
        crop = frame[cy1:cy2, x1:x2]
        return crop if crop.size > 0 else None

    def _crop_from_mask(
        self, frame: np.ndarray, mask: np.ndarray, xyxy: np.ndarray,
    ) -> np.ndarray | None:
        x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
        h = y2 - y1
        cy1 = y1 + h // 4
        cy2 = y2 - h // 4
        crop = frame[cy1:cy2, x1:x2].copy()
        crop_mask = mask[cy1:cy2, x1:x2]
        if crop.size == 0:
            return None
        crop[~crop_mask] = 0
        return crop

    def _match_numbers_to_players(
        self,
        readings: dict[int, str | None],
        number_dets: sv.Detections,
        player_dets: sv.Detections,
        validator: "NumberValidator",
        jersey_assignments: dict[int, int | None],
    ) -> None:
        if player_dets.tracker_id is None:
            return
        for det_idx, number_str in readings.items():
            if number_str is None:
                continue
            # IoS matching: find player whose bbox contains this number bbox
            num_box = number_dets.xyxy[det_idx]
            best_player_tid = None
            best_ios = 0.0
            for p_idx, p_box in enumerate(player_dets.xyxy):
                ios = self._intersection_over_smaller(num_box, p_box)
                if ios > best_ios:
                    best_ios = ios
                    best_player_tid = int(player_dets.tracker_id[p_idx])
            if best_player_tid is not None and best_ios > 0.5:
                locked = validator.update(best_player_tid, number_str)
                if locked is not None:
                    jersey_assignments[best_player_tid] = locked

    def _intersection_over_smaller(self, box_a: np.ndarray, box_b: np.ndarray) -> float:
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        intersection = (x2 - x1) * (y2 - y1)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        smaller = min(area_a, area_b)
        return intersection / smaller if smaller > 0 else 0.0

    def _build_result(
        self,
        fps: float,
        total_frames: int,
        team_assignments: dict[int, str],
        jersey_assignments: dict[int, int | None],
        movement: "MovementTracker",
        score: "ScoreTracker",
        events: list["AnalyzedEvent"],
        tracked_frames: list["TrackedFrame"],
    ) -> "AnalysisResult":
        # Compute possession percentage from events
        poss_frames: dict[str, int] = {"team_a": 0, "team_b": 0}
        current_team = None
        for tf in tracked_frames:
            for e in events:
                if e.frame == tf.frame_idx and e.type == "possession_change":
                    current_team = e.team_id
            if current_team:
                poss_frames[current_team] = poss_frames.get(current_team, 0) + 1

        total_poss = sum(poss_frames.values())
        poss_pct = {
            k: v / total_poss if total_poss > 0 else 0.0
            for k, v in poss_frames.items()
        }

        # Build per-player stats
        shot_attempts: dict[int, int] = {}
        shot_makes: dict[int, int] = {}
        passes_made: dict[int, int] = {}

        for e in events:
            pid = e.player_id
            if pid is None:
                continue
            if e.type == "shot":
                shot_attempts[pid] = shot_attempts.get(pid, 0) + 1
            elif e.type == "make":
                shot_makes[pid] = shot_makes.get(pid, 0) + 1
            elif e.type == "pass":
                passes_made[pid] = passes_made.get(pid, 0) + 1

        teams: dict[str, AnalyzedTeamStats] = {
            "team_a": AnalyzedTeamStats(
                team_id="team_a",
                score=score.scores.get("team_a", 0),
                possession_pct=poss_pct.get("team_a", 0.0),
            ),
            "team_b": AnalyzedTeamStats(
                team_id="team_b",
                score=score.scores.get("team_b", 0),
                possession_pct=poss_pct.get("team_b", 0.0),
            ),
        }

        for tid, team_id in team_assignments.items():
            jersey = jersey_assignments.get(tid)
            positions = [Point(x=x, y=y) for x, y in movement.get_positions(tid)]
            ps = AnalyzedPlayerStats(
                player_id=jersey,
                team_id=team_id,
                positions=positions,
                distance_covered_m=movement.get_distance(tid),
                shot_attempts=shot_attempts.get(tid, 0),
                shot_makes=shot_makes.get(tid, 0),
                passes_made=passes_made.get(tid, 0),
                passes_received=0,
                possession_frames=0,
            )
            if team_id in teams:
                teams[team_id].players.append(ps)

        return AnalysisResult(
            video=self._video,
            duration_seconds=total_frames / fps if fps > 0 else 0.0,
            fps=fps,
            teams=list(teams.values()),
            events=events,
            substitutions=[],
        )

    def _empty_result(self, fps: float) -> "AnalysisResult":
        return AnalysisResult(
            video=self._video,
            duration_seconds=0.0,
            fps=fps,
        )
```

- [ ] **Step 4: Run tests**

Run: `pytest open_hoops/tests/test_analyzer_new.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add open_hoops/analyzer.py open_hoops/tests/test_analyzer_new.py
git commit -m "feat: rewrite analyzer with RF-DETR + SAM2 + SigLIP pipeline"
```

---

### Task 9: Remove Old Modules and Update Tests

**Files:**
- Delete: `open_hoops/detector.py`
- Delete: `open_hoops/tracker.py`
- Delete: `open_hoops/identity/team.py`
- Delete: `open_hoops/identity/player.py`
- Delete: `open_hoops/pass_one.py`
- Delete: `open_hoops/stats/shots.py`
- Delete: `open_hoops/stats/possession.py`
- Delete: `open_hoops/stats/ball_interpolator.py`
- Delete: `open_hoops/stats/substitutions.py`
- Delete: `open_hoops/tests/test_detector.py`
- Delete: `open_hoops/tests/test_tracker.py`
- Delete: `open_hoops/tests/test_identity_team.py`
- Delete: `open_hoops/tests/test_identity_player.py`
- Delete: `open_hoops/tests/test_pass_one.py`
- Delete: `open_hoops/tests/test_stats_shots.py`
- Delete: `open_hoops/tests/test_stats_possession.py`
- Delete: `open_hoops/tests/test_ball_interpolator.py`
- Delete: `open_hoops/tests/test_substitutions.py`
- Delete: `open_hoops/tests/test_analyzer.py`
- Modify: `open_hoops/tests/conftest.py`
- Modify: `open_hoops/stats/passes.py` (update import from new tracker)
- Modify: `open_hoops/stats/movement.py` (update import from new tracker)

**Interfaces:**
- Consumes: New modules from Tasks 2-8
- Produces: Clean codebase with no dead imports or broken references

- [ ] **Step 1: Delete old modules**

```bash
rm open_hoops/detector.py
rm open_hoops/tracker.py
rm open_hoops/identity/team.py
rm open_hoops/identity/player.py
rm open_hoops/pass_one.py
rm open_hoops/stats/shots.py
rm open_hoops/stats/possession.py
rm open_hoops/stats/ball_interpolator.py
rm open_hoops/stats/substitutions.py
```

- [ ] **Step 2: Delete old tests**

```bash
rm open_hoops/tests/test_detector.py
rm open_hoops/tests/test_tracker.py
rm open_hoops/tests/test_identity_team.py
rm open_hoops/tests/test_identity_player.py
rm open_hoops/tests/test_pass_one.py
rm open_hoops/tests/test_stats_shots.py
rm open_hoops/tests/test_stats_possession.py
rm open_hoops/tests/test_ball_interpolator.py
rm open_hoops/tests/test_substitutions.py
rm open_hoops/tests/test_analyzer.py
```

- [ ] **Step 3: Update conftest.py**

```python
# open_hoops/tests/conftest.py
import numpy as np
import pytest

from open_hoops.tracking.sam2_tracker import TrackedFrame, TrackedPlayer


def make_tf(players=None, ball_pos=None, frame_idx=0):
    tf = TrackedFrame(frame_idx=frame_idx)
    tf.players = players or []
    if ball_pos is not None:
        tf.ball_pos = ball_pos
    return tf


@pytest.fixture
def blank_frame():
    return np.zeros((720, 1280, 3), dtype=np.uint8)
```

- [ ] **Step 4: Update stats/movement.py import**

Change `from open_hoops.tracker import TrackedFrame` to `from open_hoops.tracking.sam2_tracker import TrackedFrame`.

- [ ] **Step 5: Update stats/passes.py import**

Change `from open_hoops.tracker import TrackedFrame` to `from open_hoops.tracking.sam2_tracker import TrackedFrame`.

- [ ] **Step 6: Update stats/score.py** (no import changes needed — only uses AnalyzedEvent)

- [ ] **Step 7: Run full test suite**

Run: `pytest open_hoops/tests/ -v`
Expected: All remaining tests PASS (movement, passes, score, overlay, new modules)

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: remove old YOLO/BoTSORT/EasyOCR modules, update imports"
```

---

### Task 10: Update Worker Integration

**Files:**
- Modify: `worker/tasks.py`

**Interfaces:**
- Consumes: `OpenHoop` from Task 8 (same `AnalysisResult` contract)
- Produces: Working Celery task that calls new pipeline

- [ ] **Step 1: Verify worker still compiles**

The worker imports `OpenHoop` from `open_hoops.analyzer` — the class signature is the same (`Video`, `roster` kwargs). Check that the import still works:

Run: `python -c "from worker.tasks import analyze_game; print('OK')"`

If it fails, the issue is that the old `OpenHoop.__init__` took `model_path`, `src_pts`, `dst_pts` which no longer exist. The worker only passes `Video(path=...)` and `roster=roster`, so it should work unchanged.

- [ ] **Step 2: Remove any stale imports in worker if needed**

The worker imports `Video` and `Roster` from `open_hoops.service.analysis.models` — these are unchanged. No worker modifications needed.

- [ ] **Step 3: Commit (if any changes)**

```bash
git add worker/tasks.py
git commit -m "chore: verify worker integration with new analyzer"
```

---

### Task 11: Remove Training Module (no longer needed)

**Files:**
- Delete: `open_hoops/training/train.py`
- Delete: `open_hoops/training/evaluate.py`
- Delete: `open_hoops/tests/test_training_train.py`
- Delete: `open_hoops/tests/test_training_evaluate.py`

**Interfaces:**
- None — all models are pre-trained on Roboflow Universe

- [ ] **Step 1: Delete training modules**

```bash
rm open_hoops/training/train.py
rm open_hoops/training/evaluate.py
rm open_hoops/tests/test_training_train.py
rm open_hoops/tests/test_training_evaluate.py
```

- [ ] **Step 2: Keep `open_hoops/training/__init__.py` empty** (or delete directory if preferred)

```bash
rm -rf open_hoops/training/
```

- [ ] **Step 3: Run full test suite**

Run: `pytest open_hoops/tests/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove training module (all models pre-trained on Roboflow)"
```

---

### Task 12: Final Verification

**Files:**
- None created/modified

- [ ] **Step 1: Run full test suite**

Run: `pytest open_hoops/tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run linter**

Run: `ruff check open_hoops/`
Expected: No errors (fix any that appear)

- [ ] **Step 3: Run type checker**

Run: `mypy open_hoops/ --ignore-missing-imports`
Expected: No errors (fix any that appear)

- [ ] **Step 4: Verify imports are clean**

Run: `python -c "from open_hoops.analyzer import OpenHoop; print('OK')"`
Run: `python -c "from worker.tasks import analyze_game; print('OK')"`

- [ ] **Step 5: Final commit if any fixes**

```bash
git add -A
git commit -m "chore: fix lint and type errors from pipeline upgrade"
```
