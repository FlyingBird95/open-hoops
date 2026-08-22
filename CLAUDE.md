# Open Hoops

Basketball video analytics platform. YOLO-based detection + stats extraction from game footage.

## Git Workflow

- **Never push directly to `main`.** All changes go through feature branches + pull requests. No exceptions.
- **Never use `git push origin main`** — always create a PR and merge via GitHub.
- Branch naming: `feat/<short-description>`, `fix/<short-description>`, `chore/<short-description>`.
- GitHub branch protection enforces this — direct pushes to `main` are blocked.
- PRs require at least one approving review before merge (admin can bypass).
- CI must pass (Python tests + lint, Frontend type check + lint + test + build) before merge.
- Always use a worktree for feature work to keep `main` clean locally.

## Project Structure

```
open_hoops/          — core library (analysis, detection, Pydantic models)
open_hoops/core/     — database engine, Base, session factory
open_hoops/service/  — SQLAlchemy models per domain (team, player, game, event, stats)
backend/             — FastAPI REST API
worker/              — Celery worker (background analysis tasks)
frontend/            — React + TypeScript + Vite dashboard
```

## Python Style

- **Never use `from __future__ import annotations`.** Use string annotations (`"ClassName"`) for forward references instead.
- **Every `__init__.py` must be empty.** No re-exports. Import directly from the module where things are defined (e.g. `from open_hoops.service.team.models import Team`, not `from open_hoops.service import Team`).

## Key Conventions

### IDs and UIDs

- Database tables use `id: int` (auto-increment) as primary key for all internal joins/FKs.
- Every table also has `uid: str(32)` — a 32-character hex string (UUID without hyphens).
- API endpoints expose ONLY `uid`. Never expose internal `id` in responses or accept it in requests.
- Generate UIDs with `uuid.uuid4().hex` (produces 32-char lowercase hex, no hyphens).

### Team Model

- Single `Team` table serves both "my team" and opponents.
- Differentiated by `is_own: bool` column.
- Frontend shows separate pages (My Team vs Opponents) but both hit `/api/teams` with `?is_own=` filter.

### Player Model

- Player always belongs to a team (`team_id` FK).
- Identified by `jersey_number` (int) within a team.

### Game Upload & Analysis

- Game references two teams: `home_team_id` (typically own team, prefilled in UI) and `away_team_id` (opponent).
- Each game also stores `home_team_color` and `away_team_color` (jersey colors worn in that game).
- Upload triggers Celery task. Status enum: pending → processing → done | failed.
- Analysis result stored as JSON blob (`GameStats.model_dump()`) in `stats_json` column.

### Backend

- FastAPI with SQLAlchemy 2.0 (sync sessions).
- DB models live in `open_hoops/service/` (shared with worker).
- Backend dispatches Celery tasks by name via `send_task()` — no direct import of worker.
- PostgreSQL database. Alembic for migrations.

### Worker

- Celery + Redis. Separate top-level `worker/` package.
- Run with: `celery -A worker.celery_app:celery worker --loglevel=info -Q analysis`
- Imports `open_hoops.service` models and `open_hoops` for analysis.

### Frontend

- React 19, TypeScript 6, Vite 8, React Router, TanStack Query.
- shadcn/ui (Tailwind-based components).
- Pages: My Team, Opponents, Games (upload + list + detail).
- Testing: Vitest + React Testing Library. Run with `npm test` from `frontend/`.
- API responses use JSON:API format. Frontend helpers `extractOne`, `extractMany`, `extractOneWithRels`, `extractManyWithRels` in `src/lib/api.ts` unwrap responses into flat objects with uid.

### Player API

- `GET /api/players?team={team_uid}` — team query param is mandatory.
- `POST /api/players` — team_uid in request body, not URL.
