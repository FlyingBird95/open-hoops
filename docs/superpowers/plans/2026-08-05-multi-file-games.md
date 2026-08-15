# Multi-File Game Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support games consisting of multiple video file uploads, stored separately with ordering, analyzed sequentially with merged stats.

**Architecture:** New `GameFile` model (one-to-many from `Game`). Remove `file_path` from `Game`. Upload endpoint accepts multiple files. Worker iterates files in order, running analysis per segment and merging stats. Frontend multi-file picker with ordering display.

**Tech Stack:** SQLAlchemy 2.0, Alembic, FastAPI (multipart), Celery, React + TanStack Query

## Global Constraints

- UIDs: 32-char hex (`uuid4().hex`), never expose `id`
- JSON:API 1.1 response format (see `backend/CLAUDE.md`)
- One endpoint per file convention
- Game upload is multipart/form-data (exception to JSON:API body format)
- Worker reads from `open_hoops.db` models shared package

---

### Task 1: GameFile DB Model + Migration

**Files:**
- Modify: `open_hoops/db/models.py`
- Modify: `open_hoops/db/__init__.py` (export new model)
- Create: `backend/alembic/versions/<auto>_add_game_files.py`
- Test: `open_hoops/tests/test_game_file_model.py`

**Interfaces:**
- Consumes: `Game` model, `Base`, `generate_uid`
- Produces: `GameFile` model with columns: `id`, `uid`, `game_id` (FK), `file_path` (String 1024), `position` (Integer), `original_filename` (String 255), `size_bytes` (BigInteger). Relationship `Game.files` → list of `GameFile` ordered by `position`.

- [ ] **Step 1: Write failing test for GameFile model**

```python
# open_hoops/tests/test_game_file_model.py
from open_hoops.db.models import GameFile, Game, generate_uid


def test_game_file_has_required_columns():
    gf = GameFile(
        uid=generate_uid(),
        game_id=1,
        file_path="uploads/abc.mp4",
        position=0,
        original_filename="game_part1.mp4",
        size_bytes=1024000,
    )
    assert gf.file_path == "uploads/abc.mp4"
    assert gf.position == 0
    assert gf.original_filename == "game_part1.mp4"
    assert gf.size_bytes == 1024000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/pvogel/vibe/open-hoops && python -m pytest open_hoops/tests/test_game_file_model.py -v`
Expected: ImportError — `GameFile` not defined

- [ ] **Step 3: Add GameFile model to models.py**

Add after the `Game` class in `open_hoops/db/models.py`:

```python
class GameFile(Base):
    __tablename__ = "game_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    file_path: Mapped[str] = mapped_column(String(1024))
    position: Mapped[int] = mapped_column(Integer, default=0)
    original_filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    game: Mapped["Game"] = relationship(back_populates="files")
```

Add to `Game` class:

```python
files: Mapped[list["GameFile"]] = relationship(
    back_populates="game", cascade="all, delete-orphan", order_by="GameFile.position"
)
```

Add `BigInteger` to SQLAlchemy imports.

- [ ] **Step 4: Export GameFile from `open_hoops/db/__init__.py`**

Add `GameFile` to the imports and `__all__` list.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/pvogel/vibe/open-hoops && python -m pytest open_hoops/tests/test_game_file_model.py -v`
Expected: PASS

- [ ] **Step 6: Generate Alembic migration**

```bash
cd /Users/pvogel/vibe/open-hoops/backend
alembic revision --autogenerate -m "add game_files table"
```

Review generated migration. It should:
- Create `game_files` table
- NOT drop `file_path` from `games` yet (backward compat during transition)

- [ ] **Step 7: Run migration against dev DB**

```bash
cd /Users/pvogel/vibe/open-hoops/backend
alembic upgrade head
```

- [ ] **Step 8: Commit**

```bash
git add open_hoops/db/models.py open_hoops/db/__init__.py open_hoops/tests/test_game_file_model.py backend/alembic/versions/
git commit -m "feat: add GameFile model for multi-file game uploads"
```

---

### Task 2: Backend Upload Endpoint — Accept Multiple Files

**Files:**
- Modify: `backend/app/routers/games/post.py`
- Modify: `backend/app/routers/games/serialize.py`
- Modify: `backend/app/models.py` (re-export GameFile if needed)
- Test: `backend/tests/test_upload_multiple_files.py`

**Interfaces:**
- Consumes: `GameFile` model, `generate_uid`, `settings.upload_dir`
- Produces: `POST /api/games` now accepts `files: list[UploadFile]` (multiple). Creates `GameFile` rows per upload. Still dispatches `analyze_game` task. Response includes `file_count` attribute.

- [ ] **Step 1: Write failing test for multi-file upload**

```python
# backend/tests/test_upload_multiple_files.py
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

client = TestClient(app)


@pytest.fixture
def setup_teams(db_session):
    """Create home + away teams, return their UIDs."""
    from app.models import Team, generate_uid

    home = Team(uid=generate_uid(), name="Home", is_own=True)
    away = Team(uid=generate_uid(), name="Away", is_own=False)
    db_session.add_all([home, away])
    db_session.commit()
    return home.uid, away.uid


def test_upload_multiple_files(setup_teams, monkeypatch):
    home_uid, away_uid = setup_teams
    monkeypatch.setattr("app.routers.games.post.celery_app.send_task", lambda *a, **kw: None)

    files = [
        ("files", ("part1.mp4", io.BytesIO(b"fake1"), "video/mp4")),
        ("files", ("part2.mp4", io.BytesIO(b"fake2"), "video/mp4")),
    ]
    response = client.post(
        "/api/games",
        data={
            "name": "Test Game",
            "date": "2026-08-05",
            "home_team_uid": home_uid,
            "away_team_uid": away_uid,
        },
        files=files,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["attributes"]["file_count"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/pvogel/vibe/open-hoops/backend && python -m pytest tests/test_upload_multiple_files.py -v`
Expected: Fails — endpoint still expects single `file` param

- [ ] **Step 3: Update upload endpoint to accept multiple files**

Replace `backend/app/routers/games/post.py`:

```python
import os
import shutil
from typing import List

from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.jsonapi import document
from app.models import Team, Game, GameFile, generate_uid
from app.celery_app import celery as celery_app
from datetime import date as date_type
from .serialize import serialize_game


def upload_game(
    name: str = Form(...),
    date: date_type = Form(...),
    home_team_uid: str = Form(...),
    away_team_uid: str = Form(...),
    home_team_color: str = Form("#000000"),
    away_team_color: str = Form("#ffffff"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    home_team = db.query(Team).filter(Team.uid == home_team_uid).first()
    if not home_team:
        raise HTTPException(404, "Home team not found")
    away_team = db.query(Team).filter(Team.uid == away_team_uid).first()
    if not away_team:
        raise HTTPException(404, "Away team not found")

    if not files:
        raise HTTPException(422, "At least one file is required")

    os.makedirs(settings.upload_dir, exist_ok=True)
    game_uid = generate_uid()

    game = Game(
        uid=game_uid,
        name=name,
        date=date,
        file_path="",
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        home_team_color=home_team_color,
        away_team_color=away_team_color,
    )
    db.add(game)
    db.flush()

    for position, upload_file in enumerate(files):
        file_uid = generate_uid()
        ext = os.path.splitext(upload_file.filename or "video.mp4")[1]
        file_path = os.path.join(settings.upload_dir, f"{file_uid}{ext}")

        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)

        size_bytes = os.path.getsize(file_path)

        game_file = GameFile(
            uid=file_uid,
            game_id=game.id,
            file_path=file_path,
            position=position,
            original_filename=upload_file.filename or "video.mp4",
            size_bytes=size_bytes,
        )
        db.add(game_file)

    db.commit()
    db.refresh(game)

    celery_app.send_task("worker.tasks.analyze_game", args=[game.uid])

    return JSONResponse(content=document(data=serialize_game(game)), status_code=201)
```

- [ ] **Step 4: Update serialize_game to include file_count**

In `backend/app/routers/games/serialize.py`, add `file_count` to attributes:

```python
"file_count": len(game.files),
```

- [ ] **Step 5: Ensure GameFile is exported from app.models**

Check `backend/app/models.py` re-exports `GameFile` from `open_hoops.db`.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/pvogel/vibe/open-hoops/backend && python -m pytest tests/test_upload_multiple_files.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/games/post.py backend/app/routers/games/serialize.py backend/app/models.py backend/tests/test_upload_multiple_files.py
git commit -m "feat: upload endpoint accepts multiple files per game"
```

---

### Task 3: Game Files List Endpoint

**Files:**
- Create: `backend/app/routers/games/files.py`
- Modify: `backend/app/routers/games/router.py`
- Modify: `backend/app/routers/games/serialize.py`
- Test: `backend/tests/test_game_files_endpoint.py`

**Interfaces:**
- Consumes: `GameFile` model, `Game` model
- Produces: `GET /api/games/{uid}/files` → JSON:API collection of `game_files` resources with attributes: `original_filename`, `position`, `size_bytes`. Ordered by `position`.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_game_files_endpoint.py
def test_list_game_files(client, game_with_files):
    """game_with_files fixture creates a game with 2 GameFile rows."""
    response = client.get(f"/api/games/{game_with_files.uid}/files")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["attributes"]["position"] == 0
    assert data[1]["attributes"]["position"] == 1
    assert data[0]["type"] == "game_files"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/pvogel/vibe/open-hoops/backend && python -m pytest tests/test_game_files_endpoint.py -v`
Expected: 404 — route doesn't exist

- [ ] **Step 3: Create files endpoint**

```python
# backend/app/routers/games/files.py
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game
from .serialize import serialize_game_file


def list_game_files(uid: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")

    return JSONResponse(
        content=document(
            data=[serialize_game_file(f) for f in game.files],
            meta={"count": len(game.files)},
        )
    )
```

- [ ] **Step 4: Add serialize_game_file to serialize.py**

```python
from app.models import GameFile


def serialize_game_file(gf: GameFile) -> dict:
    return resource_object(
        type="game_files",
        uid=gf.uid,
        attributes={
            "original_filename": gf.original_filename,
            "position": gf.position,
            "size_bytes": gf.size_bytes,
        },
        relationships={
            "game": relationship_linkage("games", gf.game.uid),
        },
    )
```

- [ ] **Step 5: Register route in router.py**

Add to `backend/app/routers/games/router.py`:

```python
from .files import list_game_files

router.get("/{uid}/files")(list_game_files)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/pvogel/vibe/open-hoops/backend && python -m pytest tests/test_game_files_endpoint.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/games/files.py backend/app/routers/games/router.py backend/app/routers/games/serialize.py backend/tests/test_game_files_endpoint.py
git commit -m "feat: add GET /api/games/{uid}/files endpoint"
```

---

### Task 4: Worker — Analyze Multiple Files Sequentially

**Files:**
- Modify: `worker/tasks.py`
- Test: `worker/tests/test_analyze_multi_file.py`

**Interfaces:**
- Consumes: `Game.files` relationship (list of `GameFile` ordered by position), `OpenHoop`, `OHVideo`
- Produces: Worker iterates `game.files`, runs `OpenHoop.extract_stats()` per segment, merges results (sums durations, aggregates player/team stats, concatenates events with offset timestamps).

- [ ] **Step 1: Write failing test for multi-file analysis**

```python
# worker/tests/test_analyze_multi_file.py
from unittest.mock import patch, MagicMock
from open_hoops.db.models import Game, GameFile, GameStatus, Team, generate_uid
from open_hoops.models import GameStats, TeamStats, PlayerStats


def make_fake_stats(duration=60.0, fps=30.0):
    return GameStats(
        duration_seconds=duration,
        fps=fps,
        teams=[
            TeamStats(team_id="home", score=10, possession_pct=50.0, players=[]),
            TeamStats(team_id="away", score=8, possession_pct=50.0, players=[]),
        ],
        events=[],
    )


def test_analyze_merges_multiple_files(db_session, monkeypatch):
    home = Team(uid=generate_uid(), name="H", is_own=True)
    away = Team(uid=generate_uid(), name="A", is_own=False)
    db_session.add_all([home, away])
    db_session.flush()

    game = Game(
        uid=generate_uid(),
        name="Multi",
        date="2026-08-05",
        file_path="",
        home_team_id=home.id,
        away_team_id=away.id,
    )
    db_session.add(game)
    db_session.flush()

    for i in range(2):
        db_session.add(
            GameFile(
                uid=generate_uid(),
                game_id=game.id,
                file_path=f"uploads/part{i}.mp4",
                position=i,
                original_filename=f"part{i}.mp4",
                size_bytes=1000,
            )
        )
    db_session.commit()

    mock_oh = MagicMock()
    mock_oh.extract_stats.return_value = make_fake_stats(duration=60.0)

    with patch("worker.tasks.OpenHoop", return_value=mock_oh) as MockOH:
        from worker.tasks import analyze_game

        analyze_game(game.uid)

    db_session.refresh(game)
    assert game.status == GameStatus.done
    assert game.duration_seconds == 120.0  # 60 + 60
    assert MockOH.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/pvogel/vibe/open-hoops && python -m pytest worker/tests/test_analyze_multi_file.py -v`
Expected: Fails — worker still uses single `game.file_path`

- [ ] **Step 3: Rewrite analyze_game for multi-file support**

Replace the core logic in `worker/tasks.py`:

```python
@celery.task(name="worker.tasks.analyze_game")
def analyze_game(game_uid: str) -> None:
    from open_hoops import OpenHoop, Roster, TeamRoster
    from open_hoops.models import Video as OHVideo

    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.uid == game_uid).first()
        if not game:
            return

        game.status = GameStatus.processing
        db.commit()

        home_players = db.query(Player).filter(Player.team_id == game.home_team_id).all()
        away_players = db.query(Player).filter(Player.team_id == game.away_team_id).all()

        roster = Roster(
            home=TeamRoster(
                color=game.home_team_color,
                players=[p.jersey_number for p in home_players],
            ),
            away=TeamRoster(
                color=game.away_team_color,
                players=[p.jersey_number for p in away_players],
            ),
        )

        game_files = (
            db.query(GameFile).filter(GameFile.game_id == game.id).order_by(GameFile.position).all()
        )

        # Fallback for legacy games with file_path but no GameFile rows
        if not game_files and game.file_path:
            file_paths = [game.file_path]
        else:
            file_paths = [gf.file_path for gf in game_files]

        total_duration = 0.0
        fps = 0.0
        all_team_stats: dict[str, dict] = {}
        all_player_stats: dict[tuple[str, int], dict] = {}
        all_events = []
        frame_offset = 0

        for file_path in file_paths:
            oh = OpenHoop(OHVideo(path=file_path), roster=roster)
            stats = oh.extract_stats()

            total_duration += stats.duration_seconds
            fps = stats.fps  # use fps from last segment (should be consistent)

            for team_stat in stats.teams:
                key = team_stat.team_id
                if key not in all_team_stats:
                    all_team_stats[key] = {"score": 0, "possession_pct": 0.0, "count": 0}
                all_team_stats[key]["score"] += team_stat.score
                all_team_stats[key]["possession_pct"] += team_stat.possession_pct
                all_team_stats[key]["count"] += 1

                for ps in team_stat.players:
                    pkey = (key, ps.player_id)
                    if pkey not in all_player_stats:
                        all_player_stats[pkey] = {
                            "player_id": ps.player_id,
                            "team_id": key,
                            "distance_covered_m": 0.0,
                            "shot_attempts": 0,
                            "shot_makes": 0,
                            "passes_made": 0,
                            "passes_received": 0,
                            "possession_frames": 0,
                        }
                    s = all_player_stats[pkey]
                    s["distance_covered_m"] += ps.distance_covered_m
                    s["shot_attempts"] += ps.shot_attempts
                    s["shot_makes"] += ps.shot_makes
                    s["passes_made"] += ps.passes_made
                    s["passes_received"] += ps.passes_received
                    s["possession_frames"] += ps.possession_frames

            for event in stats.events:
                all_events.append(
                    {
                        "type": event.type,
                        "frame": event.frame + frame_offset,
                        "timestamp_sec": event.timestamp_sec
                        + (total_duration - stats.duration_seconds),
                        "team_id": event.team_id,
                        "player_id": event.player_id,
                    }
                )

            frame_offset += int(stats.duration_seconds * stats.fps)

        game.duration_seconds = total_duration
        game.fps = fps

        player_map = {}
        for p in home_players + away_players:
            player_map[(p.team_id, p.jersey_number)] = p

        for key, ts in all_team_stats.items():
            team_id = game.home_team_id if key == "home" else game.away_team_id
            avg_poss = ts["possession_pct"] / ts["count"] if ts["count"] else 0
            db.add(
                GameTeamStats(
                    game_id=game.id,
                    team_id=team_id,
                    score=ts["score"],
                    possession_pct=avg_poss,
                )
            )

        for (team_key, jersey), ps in all_player_stats.items():
            team_id = game.home_team_id if team_key == "home" else game.away_team_id
            player = player_map.get((team_id, jersey))
            db.add(
                GamePlayerStats(
                    game_id=game.id,
                    team_id=team_id,
                    player_id=player.id if player else None,
                    jersey_number=jersey,
                    distance_covered_m=ps["distance_covered_m"],
                    shot_attempts=ps["shot_attempts"],
                    shot_makes=ps["shot_makes"],
                    passes_made=ps["passes_made"],
                    passes_received=ps["passes_received"],
                    possession_frames=ps["possession_frames"],
                )
            )

        for ev in all_events:
            team_id = None
            if ev["team_id"] == "home":
                team_id = game.home_team_id
            elif ev["team_id"] == "away":
                team_id = game.away_team_id

            player = None
            if ev["player_id"] is not None and team_id is not None:
                player = player_map.get((team_id, ev["player_id"]))

            db.add(
                GameEvent(
                    game_id=game.id,
                    type=ev["type"],
                    frame=ev["frame"],
                    timestamp_sec=ev["timestamp_sec"],
                    player_id=player.id if player else None,
                    team_id=team_id,
                )
            )

        game.status = GameStatus.done
        db.commit()
    except Exception:
        db.rollback()
        game.status = GameStatus.failed
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 4: Add GameFile import to worker/tasks.py**

Add `GameFile` to the import from `open_hoops.db`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/pvogel/vibe/open-hoops && python -m pytest worker/tests/test_analyze_multi_file.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add worker/tasks.py worker/tests/test_analyze_multi_file.py
git commit -m "feat: worker analyzes multiple files per game, merges stats"
```

---

### Task 5: Frontend — Multi-File Upload UI

**Files:**
- Modify: `frontend/src/pages/Games.tsx`
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Consumes: `gamesApi.upload(formData)` (updated to send multiple files)
- Produces: File input accepts `multiple`, state holds `File[]`, form shows file count/names, FormData appends each file as `files`.

- [ ] **Step 1: Update API client type**

In `frontend/src/lib/api.ts`, add `file_count` to `Game` interface:

```typescript
export interface Game {
  uid: string;
  name: string;
  date: string;
  status: "pending" | "processing" | "done" | "failed";
  home_team_uid: string;
  away_team_uid: string;
  home_team_color: string;
  away_team_color: string;
  duration_seconds: number;
  fps: number;
  file_count: number;
}
```

- [ ] **Step 2: Update Games.tsx for multi-file state**

Replace single file state and input:

```tsx
const [files, setFiles] = useState<File[]>([]);
```

Update mutation to append multiple files:

```tsx
const upload = useMutation({
  mutationFn: () => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("date", date);
    formData.append("home_team_uid", homeTeam!.uid);
    formData.append("away_team_uid", awayUid);
    formData.append("home_team_color", homeColor || homeTeam!.home_color);
    formData.append("away_team_color", awayColor || awayTeam!.home_color);
    files.forEach((f) => formData.append("files", f));
    return gamesApi.upload(formData);
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["games"] });
    setName("");
    setDate(new Date().toISOString().slice(0, 10));
    setAwayUid("");
    setHomeColor("");
    setAwayColor("");
    setFiles([]);
  },
});
```

- [ ] **Step 3: Update file input to accept multiple**

```tsx
<div className="space-y-2">
  <Input
    type="file"
    accept="video/*"
    multiple
    onChange={(e) => setFiles(Array.from(e.target.files || []))}
  />
  {files.length > 0 && (
    <p className="text-sm text-muted-foreground">
      {files.length} file{files.length > 1 ? "s" : ""} selected
      ({files.map(f => f.name).join(", ")})
    </p>
  )}
</div>
```

- [ ] **Step 4: Update button disabled condition**

```tsx
<Button onClick={() => upload.mutate()} disabled={!name || !date || !awayUid || files.length === 0}>
  Upload & Analyze
</Button>
```

- [ ] **Step 5: Add file_count to games table**

In the TableHeader, add a "Files" column. In TableBody:

```tsx
<TableCell>{v.file_count}</TableCell>
```

- [ ] **Step 6: Verify in browser**

Start dev server, test:
1. Select multiple video files
2. Verify file count displays
3. Upload succeeds
4. Games list shows file count

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Games.tsx frontend/src/lib/api.ts
git commit -m "feat: multi-file upload UI with file count display"
```

---

### Task 6: Migration to Drop Legacy file_path Column

**Files:**
- Create: `backend/alembic/versions/<auto>_drop_game_file_path.py`
- Modify: `open_hoops/db/models.py` (remove `file_path` column)
- Modify: `backend/app/routers/games/post.py` (remove `file_path=""` from Game creation)

**Interfaces:**
- Consumes: Confirmation that all existing games have been migrated to `game_files` rows
- Produces: Clean schema — `games` table no longer has `file_path`

- [ ] **Step 1: Write data migration that copies existing file_path to game_files**

Create migration:

```bash
cd /Users/pvogel/vibe/open-hoops/backend
alembic revision -m "migrate file_path to game_files"
```

Edit the generated file:

```python
def upgrade():
    conn = op.get_bind()
    games = conn.execute(
        sa.text(
            "SELECT id, uid, file_path FROM games WHERE file_path != '' AND file_path IS NOT NULL"
        )
    )
    for game in games:
        existing = conn.execute(
            sa.text("SELECT COUNT(*) FROM game_files WHERE game_id = :gid"),
            {"gid": game.id},
        ).scalar()
        if existing == 0:
            uid = uuid.uuid4().hex
            conn.execute(
                sa.text(
                    "INSERT INTO game_files (uid, game_id, file_path, position, original_filename, size_bytes) "
                    "VALUES (:uid, :gid, :path, 0, :fname, 0)"
                ),
                {
                    "uid": uid,
                    "gid": game.id,
                    "path": game.file_path,
                    "fname": game.file_path.split("/")[-1],
                },
            )


def downgrade():
    pass
```

- [ ] **Step 2: Run migration**

```bash
cd /Users/pvogel/vibe/open-hoops/backend
alembic upgrade head
```

- [ ] **Step 3: Drop file_path column (separate migration)**

```bash
alembic revision --autogenerate -m "drop file_path from games"
```

Remove `file_path` from `Game` model in `open_hoops/db/models.py` first, then generate.

- [ ] **Step 4: Remove file_path from Game constructor in post.py**

Remove `file_path=""` from the Game creation kwargs.

- [ ] **Step 5: Remove legacy fallback in worker if desired**

Remove the `if not game_files and game.file_path:` block from worker — no longer needed.

- [ ] **Step 6: Run full test suite**

```bash
cd /Users/pvogel/vibe/open-hoops && python -m pytest --tb=short
```

- [ ] **Step 7: Commit**

```bash
git add open_hoops/db/models.py backend/alembic/versions/ backend/app/routers/games/post.py worker/tasks.py
git commit -m "chore: drop legacy file_path column, migrate existing data to game_files"
```
