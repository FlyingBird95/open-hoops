# Video Analysis Pipeline Upgrade: RF-DETR + SAM2 + SmolVLM2

## Summary

Replace the current YOLO-based detection/tracking pipeline with a state-of-the-art multi-model architecture inspired by [Roboflow's basketball AI pipeline](https://www.youtube.com/watch?v=yGQb9KkvQ1Q). The new pipeline uses RF-DETR for detection, SAM2 for pixel-level tracking, SigLIP for team classification, and a fine-tuned SmolVLM2 for jersey number recognition.

## Motivation

The current pipeline has three systemic weaknesses:

1. **Detection misses** — YOLO26x loses players and ball in crowded/occluded scenes
2. **Tracking ID swaps** — BoT-SORT loses identity after occlusions, causing downstream stat corruption
3. **Event misclassification** — proximity heuristics (nearest player = possession, ball near hoop = shot) produce false positives/negatives

Each model in the new pipeline directly addresses one or more of these issues.

## Current vs Proposed Pipeline

```
Current:  YOLO26x → BoT-SORT → HSV KMeans → EasyOCR → proximity heuristics
Proposed: RF-DETR → SAM2 → SigLIP+UMAP+KMeans → SmolVLM2 → keypoint homography → shot classifier
```

## Architecture

### Layer 1: Detection — RF-DETR

**Replaces:** `open_hoops/detector.py` (YOLO wrapper)

- Fine-tune [RF-DETR-L](https://github.com/roboflow/rf-detr) on [Roboflow basketball detection dataset](https://universe.roboflow.com/roboflow-universe-projects/basketball-object-detection)
- Classes: player, ball, hoop (same as current)
- RF-DETR-L: 56.5 AP50:95 vs YOLO's ~45 — DINOv2 vision transformer backbone handles crowded scenes and partial occlusions significantly better
- Latency: ~6.8ms per frame on GPU (acceptable for async Celery worker)
- Output: bounding boxes + confidence scores per frame

**Interface:** Same `FrameDetections` dataclass output — downstream code works unchanged during migration.

### Layer 2: Tracking — SAM2

**Replaces:** Ultralytics built-in BoT-SORT tracker (currently inside `detector.detect()`)

- [SAM2](https://github.com/facebookresearch/sam2) (Meta) provides video segmentation with streaming memory
- RF-DETR detections on frame 0 → prompt SAM2 with bounding boxes
- SAM2 propagates pixel-level masks across all subsequent frames with persistent IDs
- New detections appearing mid-video (subs entering) prompt SAM2 with new objects
- Handles occlusions natively — streaming memory maintains identity even when player is temporarily hidden

**Key advantages over BoT-SORT:**
- Pixel-level masks (not just bboxes) enable perfect player crop isolation
- Identity is maintained through the segmentation model's memory, not re-identification heuristics
- No ID swaps after occlusions — the #1 current failure mode

**Performance:** SAM2.1-Large: 79.5 J&F @ 39.5 FPS on A100. Smaller variants available if needed.

**Output:** Per-frame dict of `{track_id: binary_mask}` + bounding boxes derived from masks.

### Layer 3: Team Classification — SigLIP + UMAP + K-Means

**Replaces:** `open_hoops/identity/team.py` (HSV histogram clustering)

- Crop player using SAM2 mask (pixel-perfect isolation, zero background noise)
- Pass crop through [SigLIP](https://huggingface.co/google/siglip-base-patch16-224) vision encoder → 768-dim embedding
- [UMAP](https://umap-learn.readthedocs.io/) reduces to 2-3 dimensions for clustering stability
- K-Means (k=2) on reduced embeddings → team_a / team_b assignment
- If roster colors provided: match cluster centroids to roster via cosine similarity on embeddings of color patches

**Why better than HSV histograms:**
- Learned semantic features understand "jersey" vs "shorts" vs "skin"
- Robust to lighting changes, shadows, camera white balance shifts
- Background bleeding eliminated by SAM2 masks (current torso crop includes court/other players)
- UMAP handles the curse of dimensionality that raw 768-dim KMeans would suffer

### Layer 4: Jersey Number OCR — Fine-tuned SmolVLM2

**Replaces:** `open_hoops/identity/player.py` (EasyOCR)

- Fine-tune [SmolVLM2-2.2B](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct) on [Roboflow jersey number OCR dataset](https://universe.roboflow.com/roboflow-universe-projects/basketball-jersey-number-recognition)
- Input: SAM2 mask-cropped torso region (clean, no background)
- Prompt: `"What is the jersey number of this basketball player?"`
- Output: integer or null
- Run every N frames (like current OCR interval), majority vote across readings

**Why better than EasyOCR:**
- VLM understands spatial context (digit position on jersey, expected number range)
- Handles motion blur, partial occlusion, unusual fonts, numbers on dark jerseys
- SAM2 masks give it clean input (no court lines, no overlapping players)
- 2.2B params, ~5.2GB VRAM — lightweight enough to run alongside detection models

### Layer 5: Court Mapping — Keypoint Detection Model

**Replaces:** Manual homography points (`_DEFAULT_SRC` / `_DEFAULT_DST` in `analyzer.py`)

- Train keypoint detector on [basketball court keypoint dataset](https://universe.roboflow.com/roboflow-universe-projects/basketball-court-keypoint-detection)
- Detects court line intersections, free-throw corners, three-point arc endpoints, center circle
- Compute homography from detected keypoints → standard court coordinates
- Run once per shot change (or every N frames for moving cameras)

**Why better than fixed homography:**
- No manual calibration required per video
- Adapts to different camera angles, zoom levels, court markings
- Handles camera movement (if re-run periodically)
- Works on any basketball court without configuration

### Layer 6: Shot Event Detection — Trained Classifier

**Replaces:** `open_hoops/stats/shots.py` (0.45m radius proximity heuristic)

- Detect shot events using ball trajectory analysis + temporal context
- Classify outcomes (make/miss) with trained model or SmolVLM2 on clip
- Roboflow provides [Make or Miss notebook](https://colab.research.google.com/github/roboflow/sports/blob/main/examples/basketball/notebooks/make_or_miss_jumpshot_classification.ipynb) as reference

**Why better than proximity heuristic:**
- Current system: ball within 0.15m of hoop center = make. Misses bank shots off glass, tip-ins, putbacks
- Current system: ball within 0.45m = attempt. False positives on passes near hoop
- Trained classifier understands shot arc, ball trajectory through net, rim bounce patterns

## Stats Modules Impact

| Module | Change |
|--------|--------|
| `stats/possession.py` | Keep proximity logic but with much better tracking data (no ID swaps = accurate possession chains) |
| `stats/passes.py` | Keep logic, better input data. Consider VLM-based detection as future enhancement |
| `stats/movement.py` | Unchanged — uses court positions which will be more accurate from keypoint homography |
| `stats/substitutions.py` | Simplified — SAM2 tracks entering/leaving players natively |
| `stats/score.py` | Unchanged — consumes shot events |
| `stats/ball_interpolator.py` | May be unnecessary — RF-DETR likely detects ball more consistently. Keep as fallback |

## New Dependencies

```
rfdetr                  # RF-DETR detection model
sam2                    # Meta SAM2 video segmentation
transformers            # SigLIP encoder + SmolVLM2
umap-learn              # UMAP dimensionality reduction
supervision             # Roboflow detection/annotation utilities
```

### Removed Dependencies
```
ultralytics             # YOLO (replaced by RF-DETR)
easyocr                 # OCR (replaced by SmolVLM2)
```

## File Changes

### New Files
- `open_hoops/detection/rfdetr.py` — RF-DETR detection wrapper
- `open_hoops/tracking/sam2_tracker.py` — SAM2 video segmentation tracker
- `open_hoops/identity/siglip_team.py` — SigLIP + UMAP + KMeans team classifier
- `open_hoops/identity/vlm_jersey.py` — SmolVLM2 jersey number reader
- `open_hoops/court/keypoint_detector.py` — Court keypoint detection + homography
- `open_hoops/stats/shot_classifier.py` — Trained shot make/miss classifier

### Modified Files
- `open_hoops/analyzer.py` — Wire new pipeline stages
- `open_hoops/pass_one.py` — Replace detector/tracker with new models

### Deleted Files
- `open_hoops/detector.py` — Replaced by `detection/rfdetr.py`
- `open_hoops/tracker.py` — Replaced by `tracking/sam2_tracker.py`
- `open_hoops/identity/team.py` — Replaced by `identity/siglip_team.py`
- `open_hoops/identity/player.py` — Replaced by `identity/vlm_jersey.py`
- `open_hoops/stats/shots.py` — Replaced by `stats/shot_classifier.py`

## Model Artifacts

| Model | Size | Source |
|-------|------|--------|
| RF-DETR-L (fine-tuned) | ~135MB | Train on Roboflow basketball dataset |
| SAM2.1-Large | ~2.4GB | Meta checkpoint (no fine-tuning needed) |
| SigLIP-base | ~400MB | HuggingFace (no fine-tuning needed) |
| SmolVLM2-2.2B (fine-tuned) | ~5GB | Fine-tune on jersey number dataset |
| Court keypoint detector | ~135MB | Train on Roboflow court keypoint dataset |
| Shot classifier | TBD | Train on make/miss dataset |

**Total VRAM requirement:** ~12-14GB (models can share GPU, run sequentially per stage)

## Implementation Phases

### Phase 1: Detection + Tracking (RF-DETR + SAM2)
- Replace YOLO with RF-DETR
- Replace BoT-SORT with SAM2
- Maintain same `FrameDetections` / `TrackedFrame` interfaces
- All existing stats modules work unchanged on better data

### Phase 2: Identity (SigLIP + SmolVLM2)
- Replace HSV team clustering with SigLIP embeddings
- Replace EasyOCR with fine-tuned SmolVLM2
- Both benefit from SAM2 masks (Phase 1 prerequisite)

### Phase 3: Court + Events (Keypoints + Shot Classifier)
- Replace manual homography with keypoint detection
- Replace shot proximity heuristic with trained classifier
- Consider VLM-based event detection for future complex events (screens, pick-and-roll)

## Training Requirements

| Model | Dataset | Estimated Training Time (A100) |
|-------|---------|-------------------------------|
| RF-DETR-L | Basketball detection (Roboflow) | ~2-4 hours |
| SmolVLM2 | Jersey number OCR (Roboflow) | ~4-8 hours |
| Court keypoints | Court keypoint detection (Roboflow) | ~2-4 hours |
| Shot classifier | Make/miss clips | ~2-4 hours |

## References

- [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- [SAM2 GitHub](https://github.com/facebookresearch/sam2)
- [Roboflow Supervision](https://github.com/roboflow/supervision)
- [Roboflow Sports](https://github.com/roboflow/sports)
- [Video: Basketball AI Pipeline](https://www.youtube.com/watch?v=yGQb9KkvQ1Q)
- [Reddit: Basketball AI with RF-DETR, SAM2, SmolVLM2](https://www.reddit.com/r/LocalLLaMA/comments/1pes3pu/basketball_ai_with_rfdetr_sam2_and_smolvlm2/)
- [Basketball Detection Dataset](https://universe.roboflow.com/roboflow-universe-projects/basketball-object-detection)
- [Court Keypoint Dataset](https://universe.roboflow.com/roboflow-universe-projects/basketball-court-keypoint-detection)
- [Jersey Number OCR Dataset](https://universe.roboflow.com/roboflow-universe-projects/basketball-jersey-number-recognition)
