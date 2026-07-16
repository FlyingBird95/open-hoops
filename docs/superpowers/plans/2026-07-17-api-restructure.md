# open_hoops API Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `analyze()` function and `Analyzer` class with a clean class-based API: `OpenHoop(video, model_path)` with `extract_stats() -> GameStats` and `edit_overlay(game_stats, output_path) -> Video` methods, backed by a new `Video` Pydantic model.

**Architecture:** Add `Video(path: str)` to `models.py` and change `GameStats.video_path: str` → `video: Video`. Rename `Analyzer` → `OpenHoop` in `analyzer.py`, splitting `run()` into `extract_stats()` (stats only, no video write) and `edit_overlay(game_stats, output_path)` (overlay rendering using precomputed stats, returns `Video`). Update `__init__.py` to export `OpenHoop`, `Video`, `GameStats` directly; remove `analyze()`.

**Tech Stack:** Python ≥ 3.10, Pydantic ≥ 2.0, OpenCV ≥ 4.9, existing open_hoops modules unchanged.

## Global Constraints

- Python ≥ 3.10 — use `X | Y` unions, `list[T]` built-in generics
- Pydantic ≥ 2.0 — use `model_dump()`, not `.dict()`
- `Video(path: str)` is a `BaseModel` subclass in `open_hoops/models.py`
- `GameStats.video: Video` replaces `GameStats.video_path: str`
- `OpenHoop(video: Video, model_path: str = "yolo11n.pt")`
- `OpenHoop.extract_stats() -> GameStats` — no video writing
- `OpenHoop.edit_overlay(game_stats: GameStats, output_path: str) -> Video` — re-opens source video, renders overlay using game_stats data, writes to output_path, returns `Video(path=output_path)`
- `edit_overlay` raises `ValueError` if source video cannot be opened
- Public exports: `from open_hoops import OpenHoop, Video, GameStats`
- `analyze()` function removed entirely
- No changes to `detector.py`, `tracker.py`, `identity/`, `stats/`, `overlay.py`
- All existing tests must pass after each task

---

## File Map

| File | Change |
|------|--------|
| `open_hoops/models.py` | Add `Video(path: str)`; change `GameStats.video_path: str` → `video: Video` |
| `open_hoops/analyzer.py` | Rename `Analyzer` → `OpenHoop`; update constructor; split `run()` into `extract_stats()` + `edit_overlay()` |
| `open_hoops/__init__.py` | Remove `analyze()`; export `OpenHoop`, `Video`, `GameStats` |
| `tests/test_models.py` | Add `Video` tests; update `GameStats` test for `video: Video` field |
| `tests/test_analyzer.py` | Replace all `Analyzer`/`analyze()` refs with `OpenHoop`/`Video`; add `edit_overlay` test |
| `README.md` | Update quickstart to use `OpenHoop` / `Video` API |

---

### Task 1: Add `Video` model and update `GameStats`

**Files:**
- Modify: `open_hoops/models.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `Video(path: str)` — Pydantic `BaseModel` in `open_hoops.models`
  - `GameStats.video: Video` (replaces `GameStats.video_path: str`)
  - `from open_hoops.models import Video` works

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_models.py (replace existing content entirely):
import json
from open_hoops.models import GameStats, TeamStats, PlayerStats, GameEvent, Point, Video


def test_video_model():
    v = Video(path="game.mp4")
    assert v.path == "game.mp4"
    assert json.dumps(v.model_dump())


def test_gamestats_uses_video_model():
    stats = GameStats(
        video=Video(path="game.mp4"),
        duration_seconds=60.0,
        fps=30.0,
        teams=[],
        events=[],
    )
    dumped = stats.model_dump()
    assert json.dumps(dumped)
    assert dumped["video"]["path"] == "game.mp4"


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

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/pvogel/vibe/open-hoops
pytest tests/test_models.py -v
```
Expected: FAIL — `ImportError: cannot import name 'Video'` and `TypeError` on `GameStats(video=...)`

- [ ] **Step 3: Update `open_hoops/models.py`**

Replace the entire file with:

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float
    y: float


class Video(BaseModel):
    path: str


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
    video: Video
    duration_seconds: float
    fps: float
    teams: list[TeamStats] = Field(default_factory=list)
    events: list[GameEvent] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add open_hoops/models.py tests/test_models.py
git commit -m "feat: add Video model, replace GameStats.video_path with video: Video"
```

---

### Task 2: Rename `Analyzer` → `OpenHoop`, split `run()` into `extract_stats()` + `edit_overlay()`

**Files:**
- Modify: `open_hoops/analyzer.py`
- Modify: `tests/test_analyzer.py`

**Interfaces:**
- Consumes: `Video(path: str)` from Task 1, `GameStats(video=Video(...), ...)` from Task 1
- Produces:
  - `OpenHoop(video: Video, model_path: str = "yolo11n.pt")`
  - `OpenHoop.extract_stats() -> GameStats`
  - `OpenHoop.edit_overlay(game_stats: GameStats, output_path: str) -> Video`

- [ ] **Step 1: Write failing tests**

Replace the entire content of `tests/test_analyzer.py` with:

```python
import warnings
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from open_hoops.analyzer import OpenHoop
from open_hoops.models import GameStats, Video
from open_hoops.detector import FrameDetections
from open_hoops.tracker import TrackedFrame


def make_mock_cap(n_frames=10, width=1280, height=720, fps=30.0):
    cap = MagicMock()
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    reads = [True] * n_frames + [False]
    call_count = [0]

    def _read():
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(reads):
            return reads[idx], frame
        return False, frame

    cap.read.side_effect = _read
    cap.get.side_effect = lambda prop: {
        0: fps,
        7: n_frames,
    }.get(prop, 0)
    cap.isOpened.return_value = True
    return cap


def test_invalid_video_raises_value_error():
    with patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap
        with pytest.raises(ValueError, match="Cannot open video"):
            OpenHoop(Video("nonexistent.mp4")).extract_stats()


def test_extract_stats_returns_game_stats():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=5)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = OpenHoop(Video("fake.mp4")).extract_stats()
        assert isinstance(stats, GameStats)
        assert stats.video.path == "fake.mp4"


def test_extract_stats_crosses_warmup_boundary():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=35)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        stats = OpenHoop(Video("fake.mp4")).extract_stats()
        assert isinstance(stats, GameStats)
        assert stats.fps == 30.0
        assert abs(stats.duration_seconds - 35 / 30.0) < 0.01


def test_ball_missing_warning_issued():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.Detector") as mock_det_cls,
    ):
        mock_cap_cls.return_value = make_mock_cap(n_frames=160)
        mock_det = MagicMock()
        mock_det.detect.return_value = FrameDetections()
        mock_det_cls.return_value = mock_det

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            OpenHoop(Video("fake.mp4")).extract_stats()

        msgs = [str(w.message) for w in caught]
        assert any("Ball not detected for 5+" in m for m in msgs), f"No ball warning in: {msgs}"


def test_edit_overlay_returns_video():
    with (
        patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls,
        patch("open_hoops.analyzer.cv2.VideoWriter") as mock_writer_cls,
    ):
        mock_cap = make_mock_cap(n_frames=5)
        mock_cap_cls.return_value = mock_cap
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        from open_hoops.models import GameStats, Video, TeamStats
        fake_stats = GameStats(
            video=Video(path="fake.mp4"),
            duration_seconds=5 / 30.0,
            fps=30.0,
            teams=[
                TeamStats(team_id="team_a", color="#ff0000", score=4),
                TeamStats(team_id="team_b", color="#0000ff", score=2),
            ],
            events=[],
        )

        hoops = OpenHoop(Video("fake.mp4"))
        result = hoops.edit_overlay(fake_stats, "out.mp4")
        assert isinstance(result, Video)
        assert result.path == "out.mp4"


def test_edit_overlay_raises_on_invalid_video():
    with patch("open_hoops.analyzer.cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap

        from open_hoops.models import GameStats, Video
        fake_stats = GameStats(
            video=Video(path="bad.mp4"),
            duration_seconds=1.0,
            fps=30.0,
        )
        with pytest.raises(ValueError, match="Cannot open video"):
            OpenHoop(Video("bad.mp4")).edit_overlay(fake_stats, "out.mp4")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analyzer.py -v
```
Expected: FAIL — `ImportError: cannot import name 'OpenHoop'`

- [ ] **Step 3: Rewrite `open_hoops/analyzer.py`**

Replace the entire file with:

```python
from __future__ import annotations
import math
import warnings
import cv2
import numpy as np

from open_hoops.models import GameStats, TeamStats, PlayerStats, Point, Video
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

_DEFAULT_SRC = np.array(
    [[0, 0], [1280, 0], [1280, 720], [0, 720]], dtype=np.float32
)
_DEFAULT_DST = np.array(
    [[0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]], dtype=np.float32
)

_BALL_MISSING_WARN_FRAMES = 5 * 30  # baseline at 30 fps


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class OpenHoop:
    def __init__(
        self,
        video: Video,
        model_path: str = "yolo11n.pt",
        src_pts: np.ndarray | None = None,
        dst_pts: np.ndarray | None = None,
    ) -> None:
        self._video = video
        self._model_path = model_path
        self._src = src_pts if src_pts is not None else _DEFAULT_SRC
        self._dst = dst_pts if dst_pts is not None else _DEFAULT_DST

    def extract_stats(self) -> GameStats:
        """Run detection/tracking/stats pipeline. Returns GameStats. Does not write video."""
        cap = cv2.VideoCapture(self._video.path)
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video: {self._video.path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

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

        all_events = []
        player_teams: dict[int, str] = {}
        warmup_frames: list[np.ndarray] = []
        warmup_bboxes: list[list[tuple[int, int, int, int]]] = []

        frame_idx = 0
        ball_missing_count = 0
        warn_threshold = int(_BALL_MISSING_WARN_FRAMES * (fps / 30.0)) if fps > 0 else _BALL_MISSING_WARN_FRAMES

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            fd = detector.detect(frame)
            tf = tracker.update(fd, frame_idx)

            if frame_idx < 30:
                warmup_frames.append(frame)
                warmup_bboxes.append([p.bbox for p in fd.players])
            elif frame_idx == 30:
                team_clf.fit(warmup_frames, warmup_bboxes)
                warmup_frames.clear()
                warmup_bboxes.clear()

            for p in fd.players:
                if p.track_id is None:
                    continue
                team = team_clf.assign(frame, p.bbox) if frame_idx >= 30 else "team_a"
                player_teams[p.track_id] = team
                player_ident.identify(frame, p.bbox, p.track_id)

            if tf.ball_pos is None:
                ball_missing_count += 1
                if ball_missing_count == warn_threshold:
                    warnings.warn(f"Ball not detected for 5+ seconds at frame {frame_idx}")
            else:
                ball_missing_count = 0

            possession_owner: int | None = None
            if tf.players and tf.ball_pos is not None:
                nearest = min(tf.players, key=lambda p: _dist(p.court_pos, tf.ball_pos))
                possession_owner = nearest.track_id

            poss_events = possession.update(tf, player_teams, frame_idx, fps)
            shot_events = shots.update(tf, player_teams, possession_owner, frame_idx, fps)
            shot_this_frame = any(e.type == "shot" for e in shot_events)
            pass_events = passes.update(tf, player_teams, possession_owner, frame_idx, fps, shot_this_frame)
            movement.update(tf)
            score.update(shot_events)

            all_events.extend(poss_events + shot_events + pass_events)
            frame_idx += 1

        cap.release()
        return self._build_stats(fps, frame_idx, player_teams, player_ident, movement, possession, score, team_clf, all_events)

    def edit_overlay(self, game_stats: GameStats, output_path: str) -> Video:
        """Render score HUD onto source video using precomputed game_stats. Writes to output_path."""
        cap = cv2.VideoCapture(self._video.path)
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video: {self._video.path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        overlay = Overlay()

        scores = {t.team_id: t.score for t in game_stats.teams}
        team_colors = {t.team_id: t.color for t in game_stats.teams}

        writer: cv2.VideoWriter | None = None
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if writer is None:
                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            annotated = overlay.render(frame, scores, team_colors, frame_idx, fps)
            writer.write(annotated)
            frame_idx += 1

        cap.release()
        if writer:
            writer.release()

        return Video(path=output_path)

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
        events: list,
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
            video=self._video,
            duration_seconds=total_frames / fps if fps > 0 else 0.0,
            fps=fps,
            teams=list(teams.values()),
            events=events,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_analyzer.py -v
```
Expected: 6 passed

- [ ] **Step 5: Run full suite to check no regressions**

```bash
pytest -v
```
Expected: all pass (some tests in other files may fail if they reference `Analyzer` or `video_path` — those are fixed in Task 3)

- [ ] **Step 6: Commit**

```bash
git add open_hoops/analyzer.py tests/test_analyzer.py
git commit -m "feat: rename Analyzer to OpenHoop, add extract_stats() and edit_overlay()"
```

---

### Task 3: Update `__init__.py` + fix any remaining `video_path` / `Analyzer` references

**Files:**
- Modify: `open_hoops/__init__.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `OpenHoop` from Task 2, `Video` / `GameStats` from Task 1
- Produces:
  - `from open_hoops import OpenHoop, Video, GameStats` works
  - `analyze()` removed
  - README shows new API

- [ ] **Step 1: Check for remaining `video_path` or `Analyzer` references**

```bash
grep -rn "video_path\|Analyzer\|analyze(" /Users/pvogel/vibe/open-hoops/open_hoops /Users/pvogel/vibe/open-hoops/tests /Users/pvogel/vibe/open-hoops/README.md
```
Expected: only `video_path` in stats that reference `GameStats` fields may appear — confirm nothing broken.

- [ ] **Step 2: Write failing test for public import surface**

Add a new test file:

```python
# tests/test_public_api.py
from open_hoops import OpenHoop, Video, GameStats


def test_public_imports():
    assert OpenHoop is not None
    assert Video is not None
    assert GameStats is not None


def test_video_construction():
    v = Video(path="game.mp4")
    assert v.path == "game.mp4"


def test_open_hoop_construction():
    hoops = OpenHoop(Video("game.mp4"))
    assert hoops is not None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_public_api.py -v
```
Expected: FAIL — `ImportError: cannot import name 'OpenHoop'`

- [ ] **Step 4: Update `open_hoops/__init__.py`**

Replace the entire file with:

```python
from open_hoops.analyzer import OpenHoop
from open_hoops.models import Video, GameStats

__all__ = ["OpenHoop", "Video", "GameStats"]
```

- [ ] **Step 5: Run new test to verify it passes**

```bash
pytest tests/test_public_api.py -v
```
Expected: 3 passed

- [ ] **Step 6: Update README.md quickstart section**

Replace the `## Quickstart` section (lines 40–58 of current README) with:

```markdown
## Quickstart

```python
from open_hoops import OpenHoop, Video

# Load a video
video = Video(path="game.mp4")
hoops = OpenHoop(video)

# Extract stats
stats = hoops.extract_stats()
print(f"Final score: {stats.teams[0].score} – {stats.teams[1].score}")
print(f"Game duration: {stats.duration_seconds / 60:.1f} minutes")

# Render score overlay onto video
out = hoops.edit_overlay(stats, output_path="game_scored.mp4")
print(f"Annotated video saved to: {out.path}")

# Export everything to JSON
import json
with open("stats.json", "w") as f:
    json.dump(stats.model_dump(), f, indent=2)
```
```

Also update the example JSON output block — replace `"video_path": "game.mp4"` with:

```json
"video": { "path": "game.mp4" },
```

- [ ] **Step 7: Run full suite**

```bash
pytest -v
```
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add open_hoops/__init__.py README.md tests/test_public_api.py
git commit -m "feat: update public API exports, remove analyze(), update README"
```

---

## Self-Review Against Spec

| Spec requirement | Task |
|-----------------|------|
| `Video(path: str)` Pydantic model | Task 1 |
| `GameStats.video: Video` (replaces `video_path: str`) | Task 1 |
| `OpenHoop(video: Video, model_path: str = "yolo11n.pt")` | Task 2 |
| `extract_stats() -> GameStats` (no video write) | Task 2 |
| `edit_overlay(game_stats, output_path) -> Video` | Task 2 |
| `edit_overlay` raises `ValueError` on bad video | Task 2 |
| `from open_hoops import OpenHoop, Video, GameStats` | Task 3 |
| `analyze()` removed | Task 3 |
| README updated | Task 3 |
| No changes to internals (detector, tracker, etc.) | All tasks — internals untouched |
