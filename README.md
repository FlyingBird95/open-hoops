<p align="center">
  <h1 align="center">Open Hoops</h1>
  <p align="center"><strong>Drop a basketball video. Get NBA-level analytics.</strong></p>
</p>

---

Self-hosted basketball analytics platform. Point a camera at a court, upload the footage, and get back every stat — shots, scores, possession, passes, player movement, jersey numbers. No cloud. No API keys. Your data stays yours.

## What you get

| Stat | Detail |
|------|--------|
| **Shots** | Attempts, makes, misses — per player |
| **Score** | Live score tracked from confirmed makes |
| **Possession** | Ball carrier, team possession % |
| **Passes** | Pass counts per player and team |
| **Movement** | Real court positions, distance in meters |
| **Player ID** | Jersey numbers via OCR, teams by jersey color |
| **Events** | Timestamped feed — every make, miss, pass, possession change |

Plus a web dashboard that lets you browse games, compare teams, and drill into individual player performance.

---

## Stack

```
┌─────────────────────────────────────────────────────┐
│  Frontend        React + TypeScript + Vite           │
│                  TanStack Query · shadcn/ui          │
├─────────────────────────────────────────────────────┤
│  API             FastAPI + SQLAlchemy                │
│                  JSON:API responses · PostgreSQL     │
├─────────────────────────────────────────────────────┤
│  Worker          Celery + Redis                     │
│                  Background video analysis           │
├─────────────────────────────────────────────────────┤
│  Analysis        YOLO detection · ByteTrack         │
│  Engine          EasyOCR · Homography mapping       │
│                  Pydantic models · OpenCV overlay    │
└─────────────────────────────────────────────────────┘
```

---

## Getting started

```bash
git clone https://github.com/FlyingBird95/open-hoops
cd open-hoops
```

### Backend + Worker

```bash
# Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Start PostgreSQL and Redis (or use Docker)
# Then run migrations
alembic -c backend/alembic.ini upgrade head

# Start the API
uvicorn backend.app.main:app --reload

# Start the worker (separate terminal)
celery -A worker.celery_app:celery worker --loglevel=info -Q analysis
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — upload a game and watch the stats roll in.

---

## How it works

```
Video frames
  → YOLO detection    (players, ball, hoop — every frame)
  → ByteTrack         (stable track IDs across the full game)
  → Jersey color      (roster matching or K-means clustering → team assignment)
  → OCR               (EasyOCR → jersey numbers, filtered by roster)
  → Court mapping     (homography → real NBA court dimensions: 28.65m × 15.24m)
  → Stats extraction  (possession, shots, passes, movement — all parallel)
  → GameStats         (Pydantic model → JSON → database → dashboard)
```

Upload triggers a Celery task. Analysis runs in the background. Results appear in the dashboard when done.

---

## Use it as a library

The analysis engine works standalone:

```python
from open_hoops import OpenHoop, Video

stats = OpenHoop(Video("game.mp4")).extract_stats()
print(f"Final score: {stats.teams[0].score} – {stats.teams[1].score}")
```

### With a roster (better accuracy)

```python
from open_hoops import OpenHoop, Roster, TeamRoster, Video

roster = Roster(
    home=TeamRoster(color="#ffffff", players=[3, 11, 23, 30, 42]),
    away=TeamRoster(color="#1d428a", players=[1, 7, 13, 24, 35]),
)

stats = OpenHoop(Video("game.mp4"), roster=roster).extract_stats()
```

Providing jersey colors and numbers improves team classification and reduces OCR false reads.

---

## Example output

```json
{
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
          "distance_covered_m": 4821.3,
          "shot_attempts": 14,
          "shot_makes": 8,
          "passes_made": 47,
          "passes_received": 39
        }
      ]
    }
  ],
  "events": [
    { "type": "make", "frame": 312, "timestamp_sec": 10.4, "player_id": 23 },
    { "type": "possession_change", "frame": 330, "timestamp_sec": 11.0, "player_id": 11 }
  ]
}
```

---

## Development

```bash
# Python tests
pytest -v

# Lint + format
ruff check . && ruff format --check .

# Frontend
cd frontend && npm run lint && npm test
```

All tests use synthetic fixtures — no real video files needed.

---

## Requirements

- Python 3.10+
- Node.js 22+
- PostgreSQL + Redis
- Fixed-angle court camera footage (broadcast or gym-ceiling angles work best)
- YOLO weights auto-download on first run

---

## License

MIT
