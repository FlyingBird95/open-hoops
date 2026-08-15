# Open Hoops

Basketball video analytics platform. YOLO-based detection + stats extraction from game footage.

## Project Structure

```
open_hoops/    — core analysis library (Python, Pydantic models)
backend/       — FastAPI REST API + SQLAlchemy + Celery
frontend/      — React + TypeScript + Vite dashboard
```

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

### Video Upload & Analysis

- Video references two teams: `home_team_id` (typically own team, prefilled in UI) and `away_team_id` (opponent).
- Upload triggers Celery task. Status enum: pending → processing → done | failed.
- Analysis result stored as JSON blob (`GameStats.model_dump()`) in `stats_json` column.

### Backend

- FastAPI with SQLAlchemy 2.0 (sync sessions, async endpoints via `run_in_executor` where needed).
- Celery + Redis for background video analysis.
- PostgreSQL database.
- Alembic for migrations.

### Frontend

- React 19, TypeScript 6, Vite 8, React Router, TanStack Query.
- shadcn/ui (Tailwind-based components).
- Pages: My Team, Opponents, Games (upload + list + detail).
- Testing: Vitest + React Testing Library. Run with `npm test`.
- API responses use JSON:API format. Helpers in `src/lib/api.ts` unwrap responses.

### Player API

- `GET /api/players?team={team_uid}` — team query param is mandatory.
- `POST /api/players` — team_uid in request body, not URL.
