# Video Analysis Pipeline Upgrade: RF-DETR + SAM2 + SmolVLM2

## Summary

Replace the current YOLO-based detection/tracking pipeline with a state-of-the-art multi-model architecture matching [Roboflow's basketball AI pipeline](https://www.youtube.com/watch?v=yGQb9KkvQ1Q). The new pipeline uses RF-DETR for detection (including player states and shot events), SAM2 for pixel-level tracking, SigLIP for team classification, a fine-tuned SmolVLM2 for jersey number recognition, and a keypoint model for automatic court homography.

Reference implementation: [Roboflow Notebook](https://colab.research.google.com/github/roboflow-ai/notebooks/blob/main/notebooks/basketball-ai-how-to-detect-track-and-identify-basketball-players.ipynb)

## Motivation

The current pipeline has three systemic weaknesses:

1. **Detection misses** — YOLO26x loses players and ball in crowded/occluded scenes
2. **Tracking ID swaps** — BoT-SORT loses identity after occlusions, causing downstream stat corruption
3. **Event misclassification** — proximity heuristics (nearest player = possession, ball near hoop = shot) produce false positives/negatives

Each model in the new pipeline directly addresses one or more of these issues.

## Current vs Proposed Pipeline

```
Current:  YOLO26x → BoT-SORT → HSV KMeans → EasyOCR → proximity heuristics
Proposed: RF-DETR (10 classes) → SAM2 → SigLIP+UMAP+KMeans → SmolVLM2 → keypoint homography
```

## Architecture

### Layer 1: Detection — RF-DETR (10 classes)

**Replaces:** `open_hoops/detector.py` (YOLO wrapper, 3 classes)

The detection model does far more than detect players — it classifies player states and shot events directly at the detection layer.

**Model:** `basketball-player-detection-3-ycjdo/4` via [Roboflow Inference](https://inference.roboflow.com/)

**Classes (10):**

| ID | Class | Purpose |
|----|-------|---------|
| 0 | `ball` | Ball position tracking |
| 1 | `ball-in-basket` | Made shot detection (replaces proximity heuristic) |
| 2 | `number` | Jersey number region for OCR crop |
| 3 | `player` | Standard player detection |
| 4 | `player-in-possession` | Ball possession (replaces nearest-player heuristic) |
| 5 | `player-jump-shot` | Shot attempt detection |
| 6 | `player-layup-dunk` | Layup/dunk attempt detection |
| 7 | `player-shot-block` | Shot block event |
| 8 | `referee` | Referee (excluded from tracking) |
| 9 | `rim-hang` | Rim interaction |

**Configuration:**
```python
PLAYER_DETECTION_MODEL_CONFIDENCE = 0.4
PLAYER_DETECTION_MODEL_IOU_THRESHOLD = 0.9
PLAYER_CLASS_IDS = [3, 4, 5, 6, 7]  # all player-related classes
NUMBER_CLASS_ID = 2
```

**Key insight:** Shot detection, possession detection, and number localization are solved at the detection layer. No separate shot classifier or possession heuristic needed — RF-DETR handles it.

**Interface:** Uses `supervision.Detections` dataclass for interop with the rest of the Roboflow ecosystem.

### Layer 2: Tracking — SAM2

**Replaces:** Ultralytics built-in BoT-SORT tracker (currently inside `detector.detect()`)

**Model:** `sam2.1_hiera_large.pt` with `sam2.1_hiera_l.yaml` config, via [segment-anything-2-real-time](https://github.com/Gy920/segment-anything-2-real-time) fork.

**Pipeline:**
1. RF-DETR detects players on first frame (filter to `PLAYER_CLASS_IDS`)
2. Assign sequential tracker IDs: `np.arange(1, len(detections) + 1)`
3. Prompt SAM2 with player bounding boxes on first frame
4. SAM2 propagates pixel-level masks across all subsequent frames

**Implementation pattern:**
```python
class SAM2Tracker:
    def __init__(self, predictor) -> None:
        self.predictor = predictor

    def prompt_first_frame(self, frame, detections):
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            self.predictor.load_first_frame(frame)
            for xyxy, obj_id in zip(detections.xyxy, detections.tracker_id):
                bbox = np.asarray([xyxy], dtype=np.float32)
                self.predictor.add_new_prompt(
                    frame_idx=0, obj_id=int(obj_id), bbox=bbox)

    def track_frame(self, frame):
        # Returns masks + object IDs for current frame
        ...
```

**Key advantages over BoT-SORT:**
- Pixel-level masks enable perfect player crop isolation (for team classification and OCR)
- Identity is maintained through segmentation model's memory, not re-identification heuristics
- No ID swaps after occlusions — the #1 current failure mode

**Performance:** SAM2.1-Large: 79.5 J&F @ 39.5 FPS on A100. Smaller variants available if needed.

### Layer 3: Team Classification — SigLIP + UMAP + K-Means

**Replaces:** `open_hoops/identity/team.py` (HSV histogram clustering)

**Uses:** `sports.TeamClassifier` from [roboflow/sports](https://github.com/roboflow/sports) library (feat/basketball branch).

**Pipeline:**
1. Sample frames at 1 FPS
2. Detect players, extract central crops (jersey region)
3. Compute SigLIP embeddings (768-dim) for each crop
4. UMAP reduction to 3 dimensions
5. K-Means (k=2) → team_a / team_b
6. Manual mapping of cluster IDs to team names after visual inspection

**Usage:**
```python
team_classifier = TeamClassifier(device="cuda")
team_classifier.fit(crops)  # fit on sampled crops

# Per-frame assignment via track IDs (assign once, reuse)
team_id = team_classifier.predict(crop)
```

**Why better than HSV histograms:**
- Learned semantic features understand "jersey" vs "shorts" vs "skin"
- Robust to lighting changes, shadows, camera white balance shifts
- Background bleeding eliminated by SAM2 masks
- UMAP handles curse of dimensionality that raw 768-dim KMeans would suffer

### Layer 4: Jersey Number OCR — Two-Stage (RF-DETR + SmolVLM2)

**Replaces:** `open_hoops/identity/player.py` (EasyOCR on torso crop)

This is a **two-stage** pipeline, not single-stage:

**Stage 1: Number Detection (RF-DETR)**
- RF-DETR's `number` class (ID=2) detects the bounding box of jersey numbers specifically
- Much more precise than "middle third of player bbox" torso crop

**Stage 2: Number Recognition (SmolVLM2)**
- Model: `basketball-jersey-numbers-ocr/3` via Roboflow Inference (pre-fine-tuned SmolVLM2)
- Prompt: `"Read the number."`
- Input: padded crop of detected number region
- Output: digit string

**Stage 3: Temporal Validation (ConsecutiveValueTracker)**
- Number is matched to player via IoS (Intersection over Smaller Area) — if number bbox is fully inside player mask, they belong together
- `ConsecutiveValueTracker` locks a number to a track only after N consecutive consistent reads
- Prevents flickering/misreads from corrupting identity

```python
NUMBER_RECOGNITION_MODEL_ID = "basketball-jersey-numbers-ocr/3"
NUMBER_RECOGNITION_MODEL = get_model(model_id=NUMBER_RECOGNITION_MODEL_ID)
NUMBER_RECOGNITION_MODEL_PROMPT = "Read the number."
```

**Why better than EasyOCR:**
- Targeted crop from "number" detection (not generic torso region)
- Fine-tuned VLM handles motion blur, partial occlusion, unusual fonts
- Temporal validation prevents misreads from propagating
- IoS matching correctly associates numbers with players even in crowded scenes

### Layer 5: Court Mapping — Keypoint Detection + ViewTransformer

**Replaces:** Manual homography points (`_DEFAULT_SRC` / `_DEFAULT_DST` in `analyzer.py`)

**Model:** `basketball-court-detection-2/14` via Roboflow Inference

**Configuration:**
```python
KEYPOINT_DETECTION_MODEL_CONFIDENCE = 0.3
KEYPOINT_DETECTION_MODEL_ANCHOR_CONFIDENCE = 0.5
```

**Pipeline:**
1. Keypoint model detects court line intersections per frame
2. Filter to high-confidence anchor points (≥0.5)
3. Map detected keypoints to known court coordinates using `sports.basketball.CourtConfiguration`
4. Compute homography via `sports.ViewTransformer`
5. Transform player positions from pixel → court meters

**Post-processing — Path Cleaning:**
```python
cleaned_xy, edited_mask = clean_paths(
    video_xy,
    jump_sigma=3.5,       # detect jumps via robust speed analysis
    min_jump_dist=0.6,    # minimum teleport distance
    max_jump_run=18,      # max consecutive abnormal frames
    pad_around_runs=2,    # remove nearby frames
    smooth_window=9,      # Savitzky-Golay window
    smooth_poly=2,        # polynomial order
)
```

**Why better than fixed homography:**
- No manual calibration required per video
- Adapts to different camera angles, zoom levels, court markings
- Path cleaning removes teleportation artifacts from tracking glitches
- Trajectory smoothing produces clean movement paths for visualization

### Layer 6: Shot Event Detection — Detection-Level

**Replaces:** `open_hoops/stats/shots.py` (0.45m radius proximity heuristic)

Shot detection is handled entirely by the RF-DETR detection model:

| Detection Class | Event |
|----------------|-------|
| `player-jump-shot` (ID=5) | Shot attempt (jump shot) |
| `player-layup-dunk` (ID=6) | Shot attempt (layup/dunk) |
| `ball-in-basket` (ID=1) | Made basket |

**Make/Miss Classification:**
- If `ball-in-basket` detected within temporal window after shot attempt → **make**
- No `ball-in-basket` after attempt → **miss**
- Shot location mapped to court coordinates for shot chart visualization

**Why better than proximity heuristic:**
- Detects actual shooting motion, not ball proximity to hoop
- Distinguishes jump shots from layups/dunks
- `ball-in-basket` is visually confirmed (ball going through net), not distance threshold
- No false positives from passes near the hoop

## Stats Modules Impact

| Module | Change |
|--------|--------|
| `stats/possession.py` | **Replaced** — RF-DETR `player-in-possession` class detects possession directly |
| `stats/passes.py` | Keep logic but with much better tracking data. Possession changes between same-team players = pass |
| `stats/movement.py` | Enhanced — court positions from keypoint homography + path cleaning/smoothing |
| `stats/substitutions.py` | Simplified — SAM2 tracks entering/leaving players natively |
| `stats/score.py` | Simplified — consumes `ball-in-basket` detection events directly |
| `stats/shots.py` | **Replaced** — RF-DETR detects shot types and outcomes at detection layer |
| `stats/ball_interpolator.py` | May be unnecessary — RF-DETR detects ball more consistently. Keep as fallback |

## New Dependencies

```
inference               # Roboflow model hosting (wraps RF-DETR + SmolVLM2)
sam2                    # Meta SAM2 video segmentation (real-time fork)
supervision==0.27.0     # Detection/annotation/video processing utilities
sports                  # Roboflow sports lib (TeamClassifier, CourtConfiguration, ViewTransformer, clean_paths)
transformers            # SigLIP encoder (used by TeamClassifier internally)
umap-learn              # UMAP dimensionality reduction (used by TeamClassifier internally)
torch                   # PyTorch (SAM2, SigLIP inference)
```

### Removed Dependencies
```
ultralytics             # YOLO (replaced by RF-DETR via inference)
easyocr                 # OCR (replaced by SmolVLM2 via inference)
scikit-learn            # KMeans (replaced by sports.TeamClassifier)
```

## Key Utilities from Libraries

### `supervision` (sv)
- `sv.Detections` — unified detection format across models
- `sv.get_video_frames_generator()` — frame iteration
- `sv.process_video()` — video processing with callback
- `sv.MaskAnnotator`, `sv.BoxAnnotator`, `sv.LabelAnnotator` — visualization
- `sv.ColorLookup.TRACK` — consistent colors per track ID

### `sports`
- `TeamClassifier` — SigLIP + UMAP + K-Means (handles full clustering pipeline)
- `CourtConfiguration` — court dimensions and keypoint mapping
- `ViewTransformer` — homography computation from keypoints
- `ConsecutiveValueTracker` — temporal smoothing for OCR readings
- `clean_paths()` — trajectory smoothing and teleport removal
- `draw_court()`, `draw_points_on_court()`, `draw_paths_on_court()` — court visualization
- `draw_made_and_miss_on_court()` — shot chart rendering

### `inference`
- `get_model(model_id=...)` — load Roboflow-hosted models (RF-DETR, SmolVLM2)
- `.infer(frame, confidence=..., iou_threshold=...)` — run inference

## File Changes

### New Files
- `open_hoops/detection/rfdetr.py` — RF-DETR wrapper using `inference.get_model()`
- `open_hoops/tracking/sam2_tracker.py` — SAM2Tracker class (prompt + propagate)
- `open_hoops/identity/team_classifier.py` — Wraps `sports.TeamClassifier`
- `open_hoops/identity/number_reader.py` — Two-stage: RF-DETR number detection + SmolVLM2 OCR + ConsecutiveValueTracker
- `open_hoops/court/keypoint_homography.py` — Keypoint detection + ViewTransformer + clean_paths
- `open_hoops/court/visualization.py` — Court drawing utilities (wraps sports.basketball)

### Modified Files
- `open_hoops/analyzer.py` — Wire new pipeline stages
- `open_hoops/pass_one.py` — Replace detector/tracker with new models
- `open_hoops/stats/possession.py` — Use `player-in-possession` detections instead of proximity
- `open_hoops/stats/score.py` — Use `ball-in-basket` detections

### Deleted Files
- `open_hoops/detector.py` — Replaced by `detection/rfdetr.py`
- `open_hoops/tracker.py` — Replaced by `tracking/sam2_tracker.py`
- `open_hoops/identity/team.py` — Replaced by `identity/team_classifier.py`
- `open_hoops/identity/player.py` — Replaced by `identity/number_reader.py`
- `open_hoops/stats/shots.py` — Shot detection moved to detection layer

## Model Artifacts

| Model | ID | Source | Notes |
|-------|----|--------|-------|
| RF-DETR (basketball) | `basketball-player-detection-3-ycjdo/4` | Roboflow Universe (pre-trained) | 10 classes, no fine-tuning needed |
| SAM2.1-Large | `sam2.1_hiera_large.pt` | Meta checkpoint | No fine-tuning needed |
| SigLIP-base | `google/siglip-base-patch16-224` | HuggingFace | Used internally by TeamClassifier |
| SmolVLM2 (jersey OCR) | `basketball-jersey-numbers-ocr/3` | Roboflow Universe (pre-fine-tuned) | No fine-tuning needed |
| Court keypoints | `basketball-court-detection-2/14` | Roboflow Universe (pre-trained) | No fine-tuning needed |

**All models are pre-trained and available on Roboflow Universe.** No custom training required for initial implementation.

**Total VRAM requirement:** ~10-12GB (models run sequentially per stage, not all loaded simultaneously)

## Implementation Phases

### Phase 1: Detection + Tracking (RF-DETR + SAM2)
- Replace YOLO with RF-DETR (10-class model via Roboflow Inference)
- Replace BoT-SORT with SAM2Tracker
- Wire up `supervision.Detections` as the interchange format
- Shot events and possession now come from detection classes

### Phase 2: Identity (TeamClassifier + SmolVLM2)
- Replace HSV team clustering with `sports.TeamClassifier`
- Replace EasyOCR with two-stage number pipeline (RF-DETR number detect → SmolVLM2 read → ConsecutiveValueTracker validate)
- IoS matching to link numbers to player tracks

### Phase 3: Court Mapping + Visualization
- Replace manual homography with keypoint detection model
- Integrate `ViewTransformer` for pixel → court coordinate mapping
- Add `clean_paths()` post-processing for smooth trajectories
- Add court visualization (shot charts, movement paths, top-down view)

## References

- [Roboflow Notebook (reference implementation)](https://colab.research.google.com/github/roboflow-ai/notebooks/blob/main/notebooks/basketball-ai-how-to-detect-track-and-identify-basketball-players.ipynb)
- [Video: Basketball AI Pipeline](https://www.youtube.com/watch?v=yGQb9KkvQ1Q)
- [Reddit: Basketball AI with RF-DETR, SAM2, SmolVLM2](https://www.reddit.com/r/LocalLLaMA/comments/1pes3pu/basketball_ai_with_rfdetr_sam2_and_smolvlm2/)
- [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- [SAM2 Real-Time Fork](https://github.com/Gy920/segment-anything-2-real-time)
- [Roboflow Supervision](https://github.com/roboflow/supervision)
- [Roboflow Sports](https://github.com/roboflow/sports)
- [Basketball Player Detection Model](https://universe.roboflow.com/roboflow-universe-projects/basketball-player-detection-3-ycjdo)
- [Court Keypoint Detection Model](https://universe.roboflow.com/roboflow-universe-projects/basketball-court-detection-2)
- [Jersey Number OCR Model](https://universe.roboflow.com/roboflow-universe-projects/basketball-jersey-numbers-ocr)
