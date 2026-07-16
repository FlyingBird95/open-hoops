# Open-hoops

**Extract every basketball stat from a video. Powered by YOLO.**

Point `open_hoops` at any fixed-court basketball video and get back a rich JSON object — shots, scores, possession, passes, player movement, jersey numbers. No cloud. No API key. Runs entirely on your machine.

---

## What it does

| Stat | Detail |
|------|--------|
| **Shots** | Attempts, makes, misses — per player |
| **Score** | Live score tracked from confirmed makes |
| **Possession** | Who has the ball, team possession % |
| **Passes** | Pass counts per player and team |
| **Movement** | Court positions, distance covered (meters) |
| **Player identity** | Jersey numbers via OCR, team by jersey color |

Optionally render a score-overlay video with a live HUD burnt into every frame.

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

### Example output

```json
{
  "video": { "path": "game.mp4" },
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
    },
    {
      "team_id": "team_b",
      "color": "#1a6fcc",
      "score": 79,
      "possession_pct": 0.48,
      "players": []
    }
  ],
  "events": [
    {
      "type": "make",
      "frame": 312,
      "timestamp_sec": 10.4,
      "player_id": 23,
      "team_id": "team_a"
    },
    {
      "type": "possession_change",
      "frame": 330,
      "timestamp_sec": 11.0,
      "player_id": 11,
      "team_id": "team_b"
    }
  ]
}
```

---

## How it works

```
Video frames
  → YOLO detection    (players, ball, hoop detected every frame)
  → ByteTrack         (stable track IDs across the full game)
  → Jersey color      (K-means clustering → team_a / team_b assignment)
  → OCR               (EasyOCR → player jersey numbers, majority-voted every 30 frames)
  → Stats extraction  (possession, shots, passes, movement — all parallel)
  → Score overlay     (optional OpenCV HUD with live scoreboard)
  → GameStats         (Pydantic model, JSON-serializable)
```

**Key design decisions:**

- **Fixed-court optimized** — homography maps pixel coordinates to real NBA court dimensions (28.65 m × 15.24 m), so `distance_covered_m` is in actual meters
- **No cloud, no API key** — YOLO model weights are auto-downloaded by Ultralytics on first run; everything else runs local
- **Composable** — `GameStats` is a Pydantic v2 model; `.model_dump()` gives you plain JSON-ready dicts at any time
- **Safe by default** — raises `ValueError` on unreadable video; emits `warnings.warn` when the ball disappears for more than 5 seconds so you know the clip has gaps
- **OCR gracefully degrades** — `player_id` is `None` when jersey number cannot be read, rather than crashing

---

## Requirements

- Python ≥ 3.10
- A YOLO model weights file (default: `yolo11n.pt`, auto-downloaded by Ultralytics on first use)
- Fixed-angle court camera footage (broadcast-style or gym-ceiling angles work well)

---

## Development

```bash
# Install in editable mode with dev extras
pip install -e ".[dev]"

# Run all tests
pytest -v

# Lint
ruff check open_hoops/

# Type-check
mypy open_hoops/
```

All tests use synthetic fixtures — no real video files are needed.

---

## License

MIT
