# open_hoops — Design Spec

**Date:** 2026-07-16  
**Status:** Approved

---

## Goal

Python library that ingests a fixed-court-camera basketball video and extracts comprehensive game stats as JSON, with optional score overlay on output video.

---

## Architecture

Single-pass monolithic pipeline. One `Analyzer` class orchestrates all stages in sequence per video.

```
Video frames
  → Detector      (YOLO — players, ball, hoop)
  → Tracker       (ByteTrack — stable IDs across frames)
  → Identity      (jersey color clustering + OCR)
  → Stats         (possession, shots, passes, movement, score)
  → Output        (GameStats JSON + optional annotated video)
```

### Package layout

```
open_hoops/
├── __init__.py          # public API: analyze()
├── analyzer.py          # Analyzer class — orchestrates pipeline
├── detector.py          # YOLO wrapper
├── tracker.py           # ByteTrack integration
├── stats/
│   ├── __init__.py
│   ├── possession.py
│   ├── shots.py
│   ├── movement.py
│   ├── passes.py
│   └── score.py
├── identity/
│   ├── __init__.py
│   ├── team.py          # K-means jersey color clustering
│   └── player.py        # EasyOCR jersey number recognition
├── overlay.py           # Score HUD renderer
└── models.py            # Pydantic data models
```

---

## Public API

```python
from open_hoops import analyze

# Stats only
stats = analyze("game.mp4")

# Stats + annotated video with score overlay
stats = analyze("game.mp4", output_video="out.mp4")

# JSON export
import json

json.dumps(stats.model_dump())
```

`analyze()` returns a `GameStats` object (Pydantic model, fully JSON-serializable).

---

## Data Models

```
GameStats
├── video_path: str
├── duration_seconds: float
├── fps: float
├── teams: list[TeamStats]
└── events: list[GameEvent]

TeamStats
├── team_id: str              # "team_a" / "team_b"
├── color: str                # detected dominant jersey color
├── score: int
├── players: list[PlayerStats]
└── possession_pct: float

PlayerStats
├── player_id: int            # jersey number (OCR)
├── team_id: str
├── positions: list[Point]    # per-frame court coords (meters)
├── distance_covered_m: float
├── shot_attempts: int
├── shot_makes: int
├── passes_made: int
├── passes_received: int
└── possession_frames: int

GameEvent
├── type: Literal["shot", "make", "miss", "pass", "possession_change"]
├── frame: int
├── timestamp_sec: float
├── player_id: int | None
└── team_id: str | None
```

---

## Stats Extraction Logic

### Shot detection
- Ball enters hoop region (bounding box proximity) → shot attempt
- Ball trajectory passes through hoop center → make
- Ball exits hoop region without crossing center → miss

### Possession
- Nearest player to ball centroid owns possession each frame
- Possession change event fires when team ownership switches
- `possession_pct` = frames owned / total frames with detected ball

### Pass detection
- Ball moves from player A's Voronoi zone to player B's zone
- No shot attempt in transit → classified as pass

### Player movement
- Homography transform maps pixel coords → court coords (meters, standard NBA court dimensions)
- Distance = cumulative sum of frame-to-frame Euclidean displacement

### Jersey color (team assignment)
- K-means (K=2) on HSV histograms of player torso crops
- Run on first 30 frames, assignments locked for remainder of video

### Jersey OCR (player identity)
- EasyOCR on tight bounding box crop around jersey torso
- Run every 30 frames per track ID
- Majority vote over last 10 readings to stabilize assignment

### Score
- Increments team score on each confirmed make event
- Score tracked in `TeamStats.score`

### Score overlay
- Only rendered when `output_video` path is provided
- OpenCV draws HUD with team colors, current score, game clock
- Written to output video file frame-by-frame

---

## Dependencies

```toml
[project]
dependencies = [
  "ultralytics>=8.0",      # YOLO detection + ByteTrack
  "easyocr>=1.7",          # jersey number OCR
  "opencv-python>=4.9",    # video I/O + overlay
  "pydantic>=2.0",         # data models
  "numpy>=1.26",
  "scikit-learn>=1.4",     # K-means for team color clustering
]

[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]
```

---

## Error Handling

- Missing/unreadable video → raise `ValueError` with clear message
- YOLO model not found → raise `FileNotFoundError` with download hint
- Ball not detected for >5s → warn, mark stat window as `uncertain`
- OCR fails for player → `player_id = None`, tracked as unknown

---

## Testing Strategy

- Unit test each stats module with synthetic frame sequences (numpy arrays)
- Integration test `analyze()` with a short (30s) fixture video
- No mocking of YOLO — integration tests use real model inference
- Fixtures: pre-computed detection dicts to test stat logic in isolation

---

## Out of Scope

- Multi-camera / broadcast footage
- Real-time (streaming) analysis
- Web UI or CLI
- Foul/violation detection
- Audio analysis
