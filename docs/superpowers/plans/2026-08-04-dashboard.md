# Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web dashboard for managing teams/players, uploading game videos, and viewing analysis results.

**Architecture:** FastAPI backend with SQLAlchemy models + PostgreSQL. Celery + Redis for async video analysis. React frontend with shadcn/ui. Backend imports `open_hoops` library directly for analysis.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.0, Alembic, Celery, Redis, PostgreSQL | React 18, TypeScript, Vite, React Router, TanStack Query, shadcn/ui, Tailwind CSS

## Global Constraints

- All DB tables: `id: int` auto-increment PK + `uid: str(32)` unique (generated via `uuid.uuid4().hex`)
- API never exposes `id`, only `uid`
- Player API: `GET /api/players?team={team_uid}` (mandatory), `POST /api/players` with team_uid in body
- Video status enum: `pending`, `processing`, `done`, `failed`
- No auth for v1

---

### Task 1: Backend Project Scaffold + Database Models

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/.gitkeep`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Produces: `Team`, `Player`, `Video` SQLAlchemy models importable from `backend.app.models`; `get_db()` session dependency from `backend.app.database`; `settings` from `backend.app.config`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "open-hoops-backend"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
    "celery[redis]>=5.4",
    "python-multipart>=0.0.9",
    "pydantic>=2.0",
    "pydantic-settings>=2.3",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27", "pytest-asyncio>=0.23"]

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
```

- [ ] **Step 2: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/open_hoops"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: str = "uploads"

    model_config = {"env_prefix": "OPEN_HOOPS_"}


settings = Settings()
```

- [ ] **Step 3: Create `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create `backend/app/models.py`**

```python
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class VideoStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


def generate_uid() -> str:
    return uuid.uuid4().hex


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    name: Mapped[str] = mapped_column(String(255))
    is_own: Mapped[bool] = mapped_column(Boolean, default=False)
    home_color: Mapped[str] = mapped_column(String(7), default="#000000")
    away_color: Mapped[str] = mapped_column(String(7), default="#ffffff")

    players: Mapped[list["Player"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    jersey_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    team: Mapped["Team"] = relationship(back_populates="players")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(String(1024))
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    status: Mapped[VideoStatus] = mapped_column(Enum(VideoStatus), default=VideoStatus.pending)
    stats_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
```

- [ ] **Step 5: Create `backend/app/__init__.py`**

```python
```

- [ ] **Step 6: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Open Hoops API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Initialize Alembic**

Run from `backend/`:
```bash
cd backend
pip install -e ".[dev]"
alembic init alembic
```

Then edit `backend/alembic/env.py` to import models:

```python
from app.database import Base
from app.models import Team, Player, Video  # noqa: F401
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

- [ ] **Step 8: Write model tests `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def db():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

- [ ] **Step 9: Write `backend/tests/test_models.py`**

```python
from app.models import Team, Player, Video, VideoStatus, generate_uid
from datetime import date


def test_generate_uid_length():
    uid = generate_uid()
    assert len(uid) == 32
    assert uid.isalnum()


def test_team_creation(db):
    team = Team(name="Lakers", is_own=True, home_color="#552583", away_color="#fdb927")
    db.add(team)
    db.commit()
    db.refresh(team)
    assert team.id == 1
    assert len(team.uid) == 32
    assert team.is_own is True


def test_player_belongs_to_team(db):
    team = Team(name="Lakers", is_own=True)
    db.add(team)
    db.commit()
    player = Player(team_id=team.id, jersey_number=23, name="LeBron")
    db.add(player)
    db.commit()
    db.refresh(player)
    assert player.team.name == "Lakers"
    assert player.jersey_number == 23


def test_video_creation(db):
    home = Team(name="Lakers", is_own=True)
    away = Team(name="Celtics", is_own=False)
    db.add_all([home, away])
    db.commit()
    video = Video(
        name="Game 1",
        date=date(2026, 1, 15),
        file_path="/uploads/game1.mp4",
        home_team_id=home.id,
        away_team_id=away.id,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    assert video.status == VideoStatus.pending
    assert video.stats_json is None
    assert video.home_team.name == "Lakers"
```

- [ ] **Step 10: Run tests**

```bash
cd backend
pytest tests/ -v
```

- [ ] **Step 11: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold project with SQLAlchemy models"
```

---

### Task 2: Teams API (CRUD)

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/teams.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/teams.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_teams_api.py`

**Interfaces:**
- Consumes: `Team` model from `app.models`, `get_db()` from `app.database`
- Produces: Router mounted at `/api/teams` with GET (list, filter by `is_own`), POST, GET/{uid}, PUT/{uid}, DELETE/{uid}

- [ ] **Step 1: Create `backend/app/schemas/teams.py`**

```python
from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str
    is_own: bool = False
    home_color: str = "#000000"
    away_color: str = "#ffffff"


class TeamUpdate(BaseModel):
    name: str | None = None
    home_color: str | None = None
    away_color: str | None = None


class TeamResponse(BaseModel):
    uid: str
    name: str
    is_own: bool
    home_color: str
    away_color: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `backend/app/schemas/__init__.py`**

```python
```

- [ ] **Step 3: Create `backend/app/routers/teams.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Team
from app.schemas.teams import TeamCreate, TeamUpdate, TeamResponse

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
def list_teams(is_own: bool | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(Team)
    if is_own is not None:
        q = q.filter(Team.is_own == is_own)
    return q.all()


@router.post("", response_model=TeamResponse, status_code=201)
def create_team(data: TeamCreate, db: Session = Depends(get_db)):
    team = Team(**data.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/{uid}", response_model=TeamResponse)
def get_team(uid: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    return team


@router.put("/{uid}", response_model=TeamResponse)
def update_team(uid: str, data: TeamUpdate, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{uid}", status_code=204)
def delete_team(uid: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    db.delete(team)
    db.commit()
```

- [ ] **Step 4: Create `backend/app/routers/__init__.py`**

```python
```

- [ ] **Step 5: Register router in `backend/app/main.py`**

Add after CORS middleware:

```python
from app.routers import teams

app.include_router(teams.router)
```

- [ ] **Step 6: Write `backend/tests/test_teams_api.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


def test_create_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True, "home_color": "#552583"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Lakers"
    assert data["is_own"] is True
    assert len(data["uid"]) == 32


def test_list_teams_filter():
    client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    client.post("/api/teams", json={"name": "Celtics", "is_own": False})
    resp = client.get("/api/teams?is_own=true")
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Lakers"


def test_get_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    uid = resp.json()["uid"]
    resp = client.get(f"/api/teams/{uid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Lakers"


def test_update_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    uid = resp.json()["uid"]
    resp = client.put(f"/api/teams/{uid}", json={"name": "LA Lakers"})
    assert resp.json()["name"] == "LA Lakers"


def test_delete_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    uid = resp.json()["uid"]
    resp = client.delete(f"/api/teams/{uid}")
    assert resp.status_code == 204
    resp = client.get(f"/api/teams/{uid}")
    assert resp.status_code == 404
```

- [ ] **Step 7: Run tests**

```bash
cd backend
pytest tests/test_teams_api.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/ backend/app/schemas/ backend/tests/test_teams_api.py backend/app/main.py
git commit -m "feat(backend): add teams CRUD API"
```

---

### Task 3: Players API (CRUD)

**Files:**
- Create: `backend/app/routers/players.py`
- Create: `backend/app/schemas/players.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_players_api.py`

**Interfaces:**
- Consumes: `Player`, `Team` models from `app.models`, `get_db()` from `app.database`
- Produces: Router mounted at `/api/players` with GET (mandatory `team` query param), POST (team_uid in body), PUT/{uid}, DELETE/{uid}

- [ ] **Step 1: Create `backend/app/schemas/players.py`**

```python
from pydantic import BaseModel


class PlayerCreate(BaseModel):
    team_uid: str
    jersey_number: int
    name: str | None = None


class PlayerUpdate(BaseModel):
    jersey_number: int | None = None
    name: str | None = None


class PlayerResponse(BaseModel):
    uid: str
    team_uid: str
    jersey_number: int
    name: str | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `backend/app/routers/players.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Player, Team
from app.schemas.players import PlayerCreate, PlayerUpdate, PlayerResponse

router = APIRouter(prefix="/api/players", tags=["players"])


def _player_response(player: Player) -> dict:
    return {
        "uid": player.uid,
        "team_uid": player.team.uid,
        "jersey_number": player.jersey_number,
        "name": player.name,
    }


@router.get("", response_model=list[PlayerResponse])
def list_players(team: str = Query(...), db: Session = Depends(get_db)):
    team_obj = db.query(Team).filter(Team.uid == team).first()
    if not team_obj:
        raise HTTPException(404, "Team not found")
    players = db.query(Player).filter(Player.team_id == team_obj.id).all()
    return [_player_response(p) for p in players]


@router.post("", response_model=PlayerResponse, status_code=201)
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == data.team_uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    player = Player(team_id=team.id, jersey_number=data.jersey_number, name=data.name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return _player_response(player)


@router.put("/{uid}", response_model=PlayerResponse)
def update_player(uid: str, data: PlayerUpdate, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(player, key, value)
    db.commit()
    db.refresh(player)
    return _player_response(player)


@router.delete("/{uid}", status_code=204)
def delete_player(uid: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    db.delete(player)
    db.commit()
```

- [ ] **Step 3: Register router in `backend/app/main.py`**

Add:
```python
from app.routers import players

app.include_router(players.router)
```

- [ ] **Step 4: Write `backend/tests/test_players_api.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


@pytest.fixture
def team_uid():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    return resp.json()["uid"]


def test_create_player(team_uid):
    resp = client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23, "name": "LeBron"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["jersey_number"] == 23
    assert data["team_uid"] == team_uid


def test_list_players_requires_team():
    resp = client.get("/api/players")
    assert resp.status_code == 422


def test_list_players(team_uid):
    client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23})
    client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 3})
    resp = client.get(f"/api/players?team={team_uid}")
    assert len(resp.json()) == 2


def test_update_player(team_uid):
    resp = client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23})
    uid = resp.json()["uid"]
    resp = client.put(f"/api/players/{uid}", json={"name": "LeBron James"})
    assert resp.json()["name"] == "LeBron James"


def test_delete_player(team_uid):
    resp = client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23})
    uid = resp.json()["uid"]
    resp = client.delete(f"/api/players/{uid}")
    assert resp.status_code == 204
    resp = client.get(f"/api/players?team={team_uid}")
    assert len(resp.json()) == 0
```

- [ ] **Step 5: Run tests**

```bash
cd backend
pytest tests/test_players_api.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/players.py backend/app/schemas/players.py backend/tests/test_players_api.py backend/app/main.py
git commit -m "feat(backend): add players CRUD API"
```

---

### Task 4: Videos API + Celery Analysis Task

**Files:**
- Create: `backend/app/routers/videos.py`
- Create: `backend/app/schemas/videos.py`
- Create: `backend/app/celery_app.py`
- Create: `backend/app/tasks.py`
- Modify: `backend/app/main.py` (register router, create upload dir)
- Create: `backend/tests/test_videos_api.py`

**Interfaces:**
- Consumes: `Video`, `Team`, `Player` models, `get_db()`, `settings`, `Roster`/`TeamRoster`/`OpenHoop`/`Video as OHVideo` from `open_hoops`
- Produces: Router at `/api/videos` (POST upload, GET list, GET/{uid}); Celery task `analyze_video(video_uid: str)`

- [ ] **Step 1: Create `backend/app/celery_app.py`**

```python
from celery import Celery

from app.config import settings

celery = Celery("open_hoops", broker=settings.redis_url)
celery.conf.task_routes = {"app.tasks.*": {"queue": "analysis"}}
```

- [ ] **Step 2: Create `backend/app/tasks.py`**

```python
from app.celery_app import celery
from app.config import settings
from app.database import SessionLocal
from app.models import Video, Player, VideoStatus

from open_hoops import OpenHoop, Roster, TeamRoster
from open_hoops.models import Video as OHVideo


@celery.task(name="app.tasks.analyze_video")
def analyze_video(video_uid: str) -> None:
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.uid == video_uid).first()
        if not video:
            return

        video.status = VideoStatus.processing
        db.commit()

        home_players = db.query(Player).filter(Player.team_id == video.home_team_id).all()
        away_players = db.query(Player).filter(Player.team_id == video.away_team_id).all()

        roster = Roster(
            home=TeamRoster(
                color=video.home_team.home_color,
                players=[p.jersey_number for p in home_players],
            ),
            away=TeamRoster(
                color=video.away_team.away_color,
                players=[p.jersey_number for p in away_players],
            ),
        )

        oh = OpenHoop(OHVideo(path=video.file_path), roster=roster)
        stats = oh.extract_stats()

        video.stats_json = stats.model_dump()
        video.status = VideoStatus.done
        db.commit()
    except Exception:
        video.status = VideoStatus.failed
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 3: Create `backend/app/schemas/videos.py`**

```python
from pydantic import BaseModel
from datetime import date


class VideoUpload(BaseModel):
    name: str
    date: date
    home_team_uid: str
    away_team_uid: str


class VideoResponse(BaseModel):
    uid: str
    name: str
    date: date
    home_team_uid: str
    away_team_uid: str
    status: str
    stats_json: dict | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create `backend/app/routers/videos.py`**

```python
import os
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Team, Video, generate_uid
from app.schemas.videos import VideoResponse
from app.tasks import analyze_video
from datetime import date as date_type

router = APIRouter(prefix="/api/videos", tags=["videos"])


def _video_response(video: Video) -> dict:
    return {
        "uid": video.uid,
        "name": video.name,
        "date": video.date,
        "home_team_uid": video.home_team.uid,
        "away_team_uid": video.away_team.uid,
        "status": video.status.value,
        "stats_json": video.stats_json,
    }


@router.post("", response_model=VideoResponse, status_code=201)
def upload_video(
    name: str = Form(...),
    date: date_type = Form(...),
    home_team_uid: str = Form(...),
    away_team_uid: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    home_team = db.query(Team).filter(Team.uid == home_team_uid).first()
    if not home_team:
        raise HTTPException(404, "Home team not found")
    away_team = db.query(Team).filter(Team.uid == away_team_uid).first()
    if not away_team:
        raise HTTPException(404, "Away team not found")

    os.makedirs(settings.upload_dir, exist_ok=True)
    uid = generate_uid()
    ext = os.path.splitext(file.filename or "video.mp4")[1]
    file_path = os.path.join(settings.upload_dir, f"{uid}{ext}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    video = Video(
        uid=uid,
        name=name,
        date=date,
        file_path=file_path,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    analyze_video.delay(video.uid)

    return _video_response(video)


@router.get("", response_model=list[VideoResponse])
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.date.desc()).all()
    return [_video_response(v) for v in videos]


@router.get("/{uid}", response_model=VideoResponse)
def get_video(uid: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.uid == uid).first()
    if not video:
        raise HTTPException(404, "Video not found")
    return _video_response(video)
```

- [ ] **Step 5: Register router in `backend/app/main.py`**

Add:
```python
from app.routers import videos

app.include_router(videos.router)
```

- [ ] **Step 6: Write `backend/tests/test_videos_api.py`**

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


@pytest.fixture
def teams():
    home = client.post("/api/teams", json={"name": "Lakers", "is_own": True}).json()
    away = client.post("/api/teams", json={"name": "Celtics", "is_own": False}).json()
    return home["uid"], away["uid"]


@patch("app.routers.videos.analyze_video")
def test_upload_video(mock_task, teams, tmp_path):
    home_uid, away_uid = teams
    mock_task.delay.return_value = None

    resp = client.post(
        "/api/videos",
        data={
            "name": "Game 1",
            "date": "2026-01-15",
            "home_team_uid": home_uid,
            "away_team_uid": away_uid,
        },
        files={"file": ("game.mp4", BytesIO(b"fake video content"), "video/mp4")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Game 1"
    assert data["status"] == "pending"
    mock_task.delay.assert_called_once()


@patch("app.routers.videos.analyze_video")
def test_list_videos(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.delay.return_value = None

    client.post(
        "/api/videos",
        data={"name": "G1", "date": "2026-01-15", "home_team_uid": home_uid, "away_team_uid": away_uid},
        files={"file": ("g.mp4", BytesIO(b"data"), "video/mp4")},
    )
    resp = client.get("/api/videos")
    assert len(resp.json()) == 1


@patch("app.routers.videos.analyze_video")
def test_get_video(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.delay.return_value = None

    resp = client.post(
        "/api/videos",
        data={"name": "G1", "date": "2026-01-15", "home_team_uid": home_uid, "away_team_uid": away_uid},
        files={"file": ("g.mp4", BytesIO(b"data"), "video/mp4")},
    )
    uid = resp.json()["uid"]
    resp = client.get(f"/api/videos/{uid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "G1"
```

- [ ] **Step 7: Run tests**

```bash
cd backend
pytest tests/test_videos_api.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/videos.py backend/app/schemas/videos.py backend/app/celery_app.py backend/app/tasks.py backend/tests/test_videos_api.py backend/app/main.py
git commit -m "feat(backend): add videos API with Celery analysis task"
```

---

### Task 5: Frontend Scaffold + Routing

**Files:**
- Create: `frontend/` (Vite scaffold)
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/MyTeam.tsx`
- Create: `frontend/src/pages/Opponents.tsx`
- Create: `frontend/src/pages/Videos.tsx`
- Create: `frontend/src/pages/VideoDetail.tsx`

**Interfaces:**
- Consumes: Backend API at `http://localhost:8000/api/`
- Produces: Working React app with routing shell + API client

- [ ] **Step 1: Scaffold Vite + React + TypeScript**

```bash
cd /Users/pvogel/vibe/open-hoops
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom @tanstack/react-query axios
```

- [ ] **Step 2: Install Tailwind + shadcn/ui**

```bash
cd frontend
npm install -D tailwindcss @tailwindcss/vite
npx shadcn@latest init
```

Select defaults (New York style, Zinc color, CSS variables yes).

- [ ] **Step 3: Add shadcn components needed**

```bash
cd frontend
npx shadcn@latest add button input table card badge dialog form label select
```

- [ ] **Step 4: Create `frontend/src/lib/api.ts`**

```typescript
import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
});

export interface Team {
  uid: string;
  name: string;
  is_own: boolean;
  home_color: string;
  away_color: string;
}

export interface Player {
  uid: string;
  team_uid: string;
  jersey_number: number;
  name: string | null;
}

export interface Video {
  uid: string;
  name: string;
  date: string;
  home_team_uid: string;
  away_team_uid: string;
  status: "pending" | "processing" | "done" | "failed";
  stats_json: Record<string, unknown> | null;
}

export const teamsApi = {
  list: (isOwn?: boolean) =>
    api.get<Team[]>("/teams", { params: isOwn !== undefined ? { is_own: isOwn } : {} }).then((r) => r.data),
  get: (uid: string) => api.get<Team>(`/teams/${uid}`).then((r) => r.data),
  create: (data: Partial<Team>) => api.post<Team>("/teams", data).then((r) => r.data),
  update: (uid: string, data: Partial<Team>) => api.put<Team>(`/teams/${uid}`, data).then((r) => r.data),
  delete: (uid: string) => api.delete(`/teams/${uid}`),
};

export const playersApi = {
  list: (teamUid: string) => api.get<Player[]>("/players", { params: { team: teamUid } }).then((r) => r.data),
  create: (data: { team_uid: string; jersey_number: number; name?: string }) =>
    api.post<Player>("/players", data).then((r) => r.data),
  update: (uid: string, data: Partial<Player>) => api.put<Player>(`/players/${uid}`, data).then((r) => r.data),
  delete: (uid: string) => api.delete(`/players/${uid}`),
};

export const videosApi = {
  list: () => api.get<Video[]>("/videos").then((r) => r.data),
  get: (uid: string) => api.get<Video>(`/videos/${uid}`).then((r) => r.data),
  upload: (formData: FormData) => api.post<Video>("/videos", formData).then((r) => r.data),
};
```

- [ ] **Step 5: Create `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MyTeam from "./pages/MyTeam";
import Opponents from "./pages/Opponents";
import Videos from "./pages/Videos";
import VideoDetail from "./pages/VideoDetail";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-background">
          <nav className="border-b px-6 py-3 flex gap-6">
            <NavLink to="/" className={({ isActive }) => isActive ? "font-bold" : ""}>
              My Team
            </NavLink>
            <NavLink to="/opponents" className={({ isActive }) => isActive ? "font-bold" : ""}>
              Opponents
            </NavLink>
            <NavLink to="/videos" className={({ isActive }) => isActive ? "font-bold" : ""}>
              Videos
            </NavLink>
          </nav>
          <main className="p-6">
            <Routes>
              <Route path="/" element={<MyTeam />} />
              <Route path="/opponents" element={<Opponents />} />
              <Route path="/videos" element={<Videos />} />
              <Route path="/videos/:uid" element={<VideoDetail />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 6: Create placeholder pages**

`frontend/src/pages/MyTeam.tsx`:
```tsx
export default function MyTeam() {
  return <h1 className="text-2xl font-bold">My Team</h1>;
}
```

`frontend/src/pages/Opponents.tsx`:
```tsx
export default function Opponents() {
  return <h1 className="text-2xl font-bold">Opponents</h1>;
}
```

`frontend/src/pages/Videos.tsx`:
```tsx
export default function Videos() {
  return <h1 className="text-2xl font-bold">Videos</h1>;
}
```

`frontend/src/pages/VideoDetail.tsx`:
```tsx
export default function VideoDetail() {
  return <h1 className="text-2xl font-bold">Video Detail</h1>;
}
```

- [ ] **Step 7: Verify app starts**

```bash
cd frontend
npm run dev
```

Open http://localhost:5173, verify nav links render and route.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold React app with routing and API client"
```

---

### Task 6: My Team Page

**Files:**
- Modify: `frontend/src/pages/MyTeam.tsx`

**Interfaces:**
- Consumes: `teamsApi.list(true)`, `teamsApi.update()`, `playersApi.list()`, `playersApi.create()`, `playersApi.delete()`
- Produces: Full My Team page with roster table, color pickers, add/remove players

- [ ] **Step 1: Implement `MyTeam.tsx`**

```tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { teamsApi, playersApi, Team, Player } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function MyTeam() {
  const queryClient = useQueryClient();
  const [newNumber, setNewNumber] = useState("");
  const [newName, setNewName] = useState("");

  const { data: teams } = useQuery({ queryKey: ["teams", "own"], queryFn: () => teamsApi.list(true) });
  const team = teams?.[0];

  const { data: players } = useQuery({
    queryKey: ["players", team?.uid],
    queryFn: () => playersApi.list(team!.uid),
    enabled: !!team,
  });

  const updateTeam = useMutation({
    mutationFn: (data: Partial<Team>) => teamsApi.update(team!.uid, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["teams"] }),
  });

  const addPlayer = useMutation({
    mutationFn: () => playersApi.create({ team_uid: team!.uid, jersey_number: parseInt(newNumber), name: newName || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["players"] });
      setNewNumber("");
      setNewName("");
    },
  });

  const deletePlayer = useMutation({
    mutationFn: (uid: string) => playersApi.delete(uid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["players"] }),
  });

  if (!team) return <p>Loading...</p>;

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>My Team — {team.name}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4 items-center">
            <label className="text-sm">Home Color</label>
            <input
              type="color"
              value={team.home_color}
              onChange={(e) => updateTeam.mutate({ home_color: e.target.value })}
            />
            <label className="text-sm">Away Color</label>
            <input
              type="color"
              value={team.away_color}
              onChange={(e) => updateTeam.mutate({ away_color: e.target.value })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Roster</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Name</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {players?.map((p: Player) => (
                <TableRow key={p.uid}>
                  <TableCell>{p.jersey_number}</TableCell>
                  <TableCell>{p.name || "—"}</TableCell>
                  <TableCell>
                    <Button variant="destructive" size="sm" onClick={() => deletePlayer.mutate(p.uid)}>
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex gap-2 mt-4">
            <Input placeholder="#" value={newNumber} onChange={(e) => setNewNumber(e.target.value)} className="w-20" />
            <Input placeholder="Name (optional)" value={newName} onChange={(e) => setNewName(e.target.value)} />
            <Button onClick={() => addPlayer.mutate()} disabled={!newNumber}>
              Add Player
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Start backend: `cd backend && uvicorn app.main:app --reload`
Start frontend: `cd frontend && npm run dev`
Create team via API: `curl -X POST http://localhost:8000/api/teams -H "Content-Type: application/json" -d '{"name":"My Squad","is_own":true}'`
Open http://localhost:5173 — verify team loads, can add/remove players, color pickers work.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/MyTeam.tsx
git commit -m "feat(frontend): implement My Team page with roster management"
```

---

### Task 7: Opponents Page

**Files:**
- Modify: `frontend/src/pages/Opponents.tsx`

**Interfaces:**
- Consumes: `teamsApi.list(false)`, `teamsApi.create()`, `teamsApi.delete()`, `playersApi.list()`, `playersApi.create()`, `playersApi.delete()`
- Produces: Opponents list with add/delete, click to expand roster

- [ ] **Step 1: Implement `Opponents.tsx`**

```tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { teamsApi, playersApi, Team, Player } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function OpponentRoster({ team }: { team: Team }) {
  const queryClient = useQueryClient();
  const [newNumber, setNewNumber] = useState("");
  const [newName, setNewName] = useState("");

  const { data: players } = useQuery({
    queryKey: ["players", team.uid],
    queryFn: () => playersApi.list(team.uid),
  });

  const addPlayer = useMutation({
    mutationFn: () => playersApi.create({ team_uid: team.uid, jersey_number: parseInt(newNumber), name: newName || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["players", team.uid] });
      setNewNumber("");
      setNewName("");
    },
  });

  const deletePlayer = useMutation({
    mutationFn: (uid: string) => playersApi.delete(uid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["players", team.uid] }),
  });

  return (
    <div className="mt-2">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>#</TableHead>
            <TableHead>Name</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {players?.map((p: Player) => (
            <TableRow key={p.uid}>
              <TableCell>{p.jersey_number}</TableCell>
              <TableCell>{p.name || "—"}</TableCell>
              <TableCell>
                <Button variant="destructive" size="sm" onClick={() => deletePlayer.mutate(p.uid)}>
                  Remove
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="flex gap-2 mt-2">
        <Input placeholder="#" value={newNumber} onChange={(e) => setNewNumber(e.target.value)} className="w-20" />
        <Input placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <Button onClick={() => addPlayer.mutate()} disabled={!newNumber} size="sm">Add</Button>
      </div>
    </div>
  );
}

export default function Opponents() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [homeColor, setHomeColor] = useState("#000000");
  const [awayColor, setAwayColor] = useState("#ffffff");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: teams } = useQuery({ queryKey: ["teams", "opponents"], queryFn: () => teamsApi.list(false) });

  const createTeam = useMutation({
    mutationFn: () => teamsApi.create({ name, is_own: false, home_color: homeColor, away_color: awayColor }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      setName("");
    },
  });

  const deleteTeam = useMutation({
    mutationFn: (uid: string) => teamsApi.delete(uid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["teams"] }),
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Add Opponent</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 items-center">
            <Input placeholder="Team name" value={name} onChange={(e) => setName(e.target.value)} />
            <label className="text-sm">Home</label>
            <input type="color" value={homeColor} onChange={(e) => setHomeColor(e.target.value)} />
            <label className="text-sm">Away</label>
            <input type="color" value={awayColor} onChange={(e) => setAwayColor(e.target.value)} />
            <Button onClick={() => createTeam.mutate()} disabled={!name}>Add</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Opponents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {teams?.map((t: Team) => (
            <div key={t.uid} className="border rounded p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-medium">{t.name}</span>
                  <Badge style={{ backgroundColor: t.home_color }} className="w-6 h-6" />
                  <Badge style={{ backgroundColor: t.away_color }} className="w-6 h-6" />
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setExpanded(expanded === t.uid ? null : t.uid)}>
                    {expanded === t.uid ? "Hide" : "Roster"}
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => deleteTeam.mutate(t.uid)}>
                    Delete
                  </Button>
                </div>
              </div>
              {expanded === t.uid && <OpponentRoster team={t} />}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Open http://localhost:5173/opponents — add opponent, set colors, expand roster, add players.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Opponents.tsx
git commit -m "feat(frontend): implement Opponents page"
```

---

### Task 8: Videos Page (Upload + List)

**Files:**
- Modify: `frontend/src/pages/Videos.tsx`

**Interfaces:**
- Consumes: `teamsApi.list()`, `videosApi.upload()`, `videosApi.list()`
- Produces: Upload form (name, date, home prefilled, away select, file) + video list with status badges

- [ ] **Step 1: Implement `Videos.tsx`**

```tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { teamsApi, videosApi, Team, Video } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500",
  processing: "bg-blue-500",
  done: "bg-green-500",
  failed: "bg-red-500",
};

export default function Videos() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [awayUid, setAwayUid] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const { data: ownTeams } = useQuery({ queryKey: ["teams", "own"], queryFn: () => teamsApi.list(true) });
  const { data: opponents } = useQuery({ queryKey: ["teams", "opponents"], queryFn: () => teamsApi.list(false) });
  const { data: videos, refetch } = useQuery({ queryKey: ["videos"], queryFn: videosApi.list, refetchInterval: 5000 });

  const homeTeam = ownTeams?.[0];

  const upload = useMutation({
    mutationFn: () => {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("date", date);
      formData.append("home_team_uid", homeTeam!.uid);
      formData.append("away_team_uid", awayUid);
      formData.append("file", file!);
      return videosApi.upload(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      setName("");
      setDate("");
      setAwayUid("");
      setFile(null);
    },
  });

  return (
    <div className="space-y-6 max-w-3xl">
      <Card>
        <CardHeader>
          <CardTitle>Upload Video</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input placeholder="Video name" value={name} onChange={(e) => setName(e.target.value)} />
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground">Home Team</label>
              <p className="font-medium">{homeTeam?.name || "No team set"}</p>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Away Team</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={awayUid}
                onChange={(e) => setAwayUid(e.target.value)}
              >
                <option value="">Select opponent...</option>
                {opponents?.map((t: Team) => (
                  <option key={t.uid} value={t.uid}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>
          <Input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <Button onClick={() => upload.mutate()} disabled={!name || !date || !awayUid || !file}>
            Upload & Analyze
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Videos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {videos?.map((v: Video) => (
                <TableRow key={v.uid}>
                  <TableCell>
                    <Link to={`/videos/${v.uid}`} className="text-blue-600 underline">{v.name}</Link>
                  </TableCell>
                  <TableCell>{v.date}</TableCell>
                  <TableCell>
                    <Badge className={STATUS_COLORS[v.status]}>{v.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Open http://localhost:5173/videos — verify upload form renders, opponent dropdown populated, file picker works.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Videos.tsx
git commit -m "feat(frontend): implement Videos page with upload and list"
```

---

### Task 9: Video Detail Page (Stats + Events)

**Files:**
- Modify: `frontend/src/pages/VideoDetail.tsx`

**Interfaces:**
- Consumes: `videosApi.get(uid)` which returns `stats_json` containing `GameStats` shape
- Produces: Stats summary (scores, possession %, player table) + event timeline

- [ ] **Step 1: Implement `VideoDetail.tsx`**

```tsx
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { videosApi } from "../lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface PlayerStat {
  player_id: number | null;
  team_id: string;
  distance_covered_m: number;
  shot_attempts: number;
  shot_makes: number;
  passes_made: number;
  passes_received: number;
  possession_frames: number;
}

interface TeamStat {
  team_id: string;
  color: string;
  score: number;
  possession_pct: number;
  players: PlayerStat[];
}

interface GameEvent {
  type: string;
  frame: number;
  timestamp_sec: number;
  player_id: number | null;
  team_id: string | null;
}

interface GameStats {
  duration_seconds: number;
  fps: number;
  teams: TeamStat[];
  events: GameEvent[];
}

export default function VideoDetail() {
  const { uid } = useParams<{ uid: string }>();
  const { data: video } = useQuery({
    queryKey: ["video", uid],
    queryFn: () => videosApi.get(uid!),
    refetchInterval: (query) => query.state.data?.status === "done" ? false : 3000,
  });

  if (!video) return <p>Loading...</p>;

  if (video.status !== "done") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{video.name}</h1>
        <Badge>{video.status}</Badge>
        {video.status === "processing" && <p className="text-muted-foreground">Analysis in progress...</p>}
        {video.status === "failed" && <p className="text-red-500">Analysis failed.</p>}
      </div>
    );
  }

  const stats = video.stats_json as unknown as GameStats;

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">{video.name}</h1>
      <p className="text-muted-foreground">
        Duration: {(stats.duration_seconds / 60).toFixed(1)} min | FPS: {stats.fps}
      </p>

      <div className="grid grid-cols-2 gap-4">
        {stats.teams.map((team) => (
          <Card key={team.team_id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: team.color }} />
                {team.team_id}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{team.score}</p>
              <p className="text-sm text-muted-foreground">Possession: {(team.possession_pct * 100).toFixed(0)}%</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Player Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Jersey</TableHead>
                <TableHead>Team</TableHead>
                <TableHead>Shots</TableHead>
                <TableHead>Makes</TableHead>
                <TableHead>FG%</TableHead>
                <TableHead>Passes</TableHead>
                <TableHead>Distance (m)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stats.teams.flatMap((t) =>
                t.players.map((p) => (
                  <TableRow key={`${t.team_id}-${p.player_id}`}>
                    <TableCell>{p.player_id ?? "?"}</TableCell>
                    <TableCell>{t.team_id}</TableCell>
                    <TableCell>{p.shot_attempts}</TableCell>
                    <TableCell>{p.shot_makes}</TableCell>
                    <TableCell>{p.shot_attempts > 0 ? ((p.shot_makes / p.shot_attempts) * 100).toFixed(0) + "%" : "—"}</TableCell>
                    <TableCell>{p.passes_made}</TableCell>
                    <TableCell>{p.distance_covered_m.toFixed(0)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-y-auto space-y-1">
            {stats.events.map((e, i) => (
              <div key={i} className="flex gap-4 text-sm py-1 border-b">
                <span className="text-muted-foreground w-16">{e.timestamp_sec.toFixed(1)}s</span>
                <Badge variant="outline">{e.type}</Badge>
                <span>{e.team_id}</span>
                <span>#{e.player_id ?? "?"}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Navigate to a video detail page. If no analysis done yet, verify status polling. If done, verify stats render.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/VideoDetail.tsx
git commit -m "feat(frontend): implement Video Detail page with stats and events"
```

---

### Task 10: Docker Compose + Integration Wiring

**Files:**
- Create: `docker-compose.yml` (root)
- Create: `backend/Dockerfile`

**Interfaces:**
- Produces: One-command dev environment with Postgres + Redis + Backend + Celery worker

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: open_hoops
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      OPEN_HOOPS_DATABASE_URL: postgresql://postgres:postgres@db:5432/open_hoops
      OPEN_HOOPS_REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./backend:/app
      - ./open_hoops:/open_hoops
      - uploads:/app/uploads
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: ./backend
    environment:
      OPEN_HOOPS_DATABASE_URL: postgresql://postgres:postgres@db:5432/open_hoops
      OPEN_HOOPS_REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./backend:/app
      - ./open_hoops:/open_hoops
      - uploads:/app/uploads
    command: celery -A app.celery_app:celery worker --loglevel=info -Q analysis

volumes:
  pgdata:
  uploads:
```

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install -e "." && pip install -e /open_hoops

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create initial Alembic migration**

```bash
cd backend
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

- [ ] **Step 4: Test full stack**

```bash
docker compose up -d db redis
cd backend && alembic upgrade head
cd backend && uvicorn app.main:app --reload &
cd backend && celery -A app.celery_app:celery worker --loglevel=info -Q analysis &
cd frontend && npm run dev
```

Verify: create team, add players, add opponent, upload video, watch status go pending → processing → done.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml backend/Dockerfile
git commit -m "feat: add Docker Compose for Postgres, Redis, backend, and Celery worker"
```

---

Plan complete and saved to `docs/superpowers/plans/2026-08-04-dashboard.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?