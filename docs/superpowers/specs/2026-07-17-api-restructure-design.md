# open_hoops API Restructure — Design Spec

**Date:** 2026-07-17
**Status:** Approved

---

## Goal

Replace the procedural `analyze()` function and internal `Analyzer` class with a clean class-based API: `OpenHoop(video, model_path)` with `extract_stats()` and `edit_overlay(game_stats, output_path)` methods, backed by a typed `Video` model.

---

## Changes

### 1. New `Video` model (`open_hoops/models.py`)

```python
class Video(BaseModel):
    path: str
```

Simple Pydantic wrapper. Replaces bare `str` paths in the public API. `GameStats.video_path: str` becomes `GameStats.video: Video`.

### 2. `Analyzer` → `OpenHoop` (`open_hoops/analyzer.py`)

Rename `Analyzer` to `OpenHoop`. Update constructor and methods:

```python
class OpenHoop:
    def __init__(self, video: Video, model_path: str = "yolo11n.pt") -> None: ...
    def extract_stats(self) -> GameStats: ...
    def edit_overlay(self, game_stats: GameStats, output_path: str) -> Video: ...
```

- `extract_stats()` — runs detection/tracking/identity/stats pipeline. Returns `GameStats`. No video writing.
- `edit_overlay(game_stats, output_path)` — renders score HUD overlay onto the source video using precomputed `game_stats`, writes to `output_path`, returns `Video(path=output_path)`.

### 3. Updated public surface (`open_hoops/__init__.py`)

Remove `analyze()`. Export `OpenHoop` and `Video` directly:

```python
from open_hoops.analyzer import OpenHoop
from open_hoops.models import Video, GameStats

__all__ = ["OpenHoop", "Video", "GameStats"]
```

### 4. `GameStats.video_path` → `GameStats.video`

Replace `video_path: str` field with `video: Video` for consistency with the new model.

---

## Public API

```python
from open_hoops import OpenHoop, Video

# Extract stats
hoops = OpenHoop(Video("game.mp4"))
stats = hoops.extract_stats()

# Render overlay
out_video = hoops.edit_overlay(stats, "game_scored.mp4")
# out_video == Video(path="game_scored.mp4")

# JSON export
import json
json.dumps(stats.model_dump())
```

---

## Implementation Approach

Full rename (approach B): rename `Analyzer` → `OpenHoop` in `analyzer.py`, add `Video` to `models.py`, update `__init__.py`. No dead code left behind.

`edit_overlay` re-opens the source video (`self._video.path`) and replays frames through `Overlay.render()` using the provided `game_stats` for score/team data. It does not re-run YOLO — stats are passed in.

---

## Error Handling

- `extract_stats()` raises `ValueError` if video cannot be opened (unchanged)
- `edit_overlay()` raises `ValueError` if source video cannot be opened or `output_path` is not writable

---

## Files Touched

| File | Change |
|------|--------|
| `open_hoops/models.py` | Add `Video`; change `GameStats.video_path: str` → `video: Video` |
| `open_hoops/analyzer.py` | Rename `Analyzer` → `OpenHoop`; update constructor; split `run()` into `extract_stats()` + `edit_overlay()` |
| `open_hoops/__init__.py` | Remove `analyze()`; export `OpenHoop`, `Video`, `GameStats` |
| `tests/test_analyzer.py` | Update all references from `Analyzer`/`analyze()` to `OpenHoop`/`Video` |
| `tests/test_models.py` | Add `Video` model tests; update `GameStats` test for `video: Video` field |
| `README.md` | Update usage examples |

---

## Out of Scope

- No changes to detection, tracking, identity, stats, or overlay internals
- No new stats or capabilities
- No CLI
