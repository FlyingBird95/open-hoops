# Basketball Analytics Dashboard — Design Spec

## Overview

Web dashboard for uploading basketball game videos, managing teams/rosters, and viewing analysis results. React frontend + FastAPI backend + PostgreSQL + Celery.

## Architecture

```
open_hoops/        (existing analysis library, unchanged)
backend/           (FastAPI + SQLAlchemy + Celery)
frontend/          (React + TypeScript + Vite)
```

Monorepo. Backend imports `open_hoops` directly.

## Database Models (SQLAlchemy, PostgreSQL)

All tables use `id: int` as auto-increment primary key. All tables expose `uid: str(32)` (hex, no hyphens) as external identifier via API.

### Team

| Column | Type | Notes |
|--------|------|-------|
| id | int | PK, auto-increment |
| uid | str(32) | unique, hex no hyphens |
| name | str | team name |
| is_own | bool | true = user's team, false = opponent |
| home_color | str | hex color for home jersey |
| away_color | str | hex color for away jersey |

### Player

| Column | Type | Notes |
|--------|------|-------|
| id | int | PK, auto-increment |
| uid | str(32) | unique, hex no hyphens |
| team_id | int | FK → Team.id |
| jersey_number | int | jersey number |
| name | str | nullable |

### Video

| Column | Type | Notes |
|--------|------|-------|
| id | int | PK, auto-increment |
| uid | str(32) | unique, hex no hyphens |
| name | str | user-given name |
| date | date | game date |
| file_path | str | path to uploaded file on disk |
| home_team_id | int | FK → Team.id (user's team, prefilled) |
| away_team_id | int | FK → Team.id (opponent) |
| status | enum | pending, processing, done, failed |
| stats_json | JSON | nullable, GameStats.model_dump() on completion |

## API Endpoints

All endpoints use `uid` for resource identification. Internal DB operations use `id`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/teams?is_own=bool` | List teams, filterable |
| POST | `/api/teams` | Create team |
| GET | `/api/teams/{uid}` | Team detail |
| PUT | `/api/teams/{uid}` | Update team |
| DELETE | `/api/teams/{uid}` | Delete team |
| GET | `/api/players?team={uid}` | List players (team uid required) |
| POST | `/api/players` | Create player (team uid in body) |
| PUT | `/api/players/{uid}` | Update player |
| DELETE | `/api/players/{uid}` | Delete player |
| POST | `/api/videos` | Upload video + metadata, triggers analysis |
| GET | `/api/videos` | List videos with status |
| GET | `/api/videos/{uid}` | Video detail + stats |

## Analysis Flow

1. POST `/api/videos` → save file to disk, create Video row (status=pending)
2. Dispatch Celery task `analyze_video(video_uid)`
3. Celery worker:
   - Loads video, home team roster, away team roster from DB
   - Builds `Roster` from both teams' players + jersey colors
   - Runs `OpenHoop(video, roster=roster).extract_stats()`
   - Stores `GameStats.model_dump()` in `stats_json`, sets status=done
   - On error: sets status=failed
4. Frontend polls `GET /api/videos/{uid}` for status updates

## Infrastructure

- **Celery** with **Redis** as message broker
- Video files stored on local filesystem (configurable upload dir)
- No authentication for v1 (single-user local tool)

## Frontend

### Tech Stack

- React 18, TypeScript, Vite
- React Router for navigation
- TanStack Query for data fetching/caching
- shadcn/ui (Tailwind-based, copy-paste components)

### Pages

1. **My Team** — displays/edits the single `is_own=true` team. Player roster table (jersey number, name). Home/away color pickers. Calls same `/api/teams` endpoints filtered by `is_own=true`.

2. **Opponents** — lists all `is_own=false` teams. Add new opponent (name + colors). Click to edit roster. Calls same `/api/teams` endpoints filtered by `is_own=false`.

3. **Videos** — upload form: name, date, home team (prefilled with own team, selectable), away team dropdown (opponents). Below: list of all videos with status badge (pending/processing/done/failed). Click video → detail page showing stats summary (scores, possession %, per-player table) and event timeline.

## Decisions

- Single Team model for both "my team" and opponents, differentiated by `is_own` flag
- Internal DB uses integer `id` as PK; API exposes only `uid` (32-char hex, no hyphens)
- Video references two teams: home_team (prefilled) and away_team (selected)
- Celery for async analysis (not asyncio.to_thread) to support horizontal scaling later
- Frontend and backend in same repo alongside existing `open_hoops` library
