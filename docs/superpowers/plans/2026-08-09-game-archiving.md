# Game Archiving Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ability to archive/unarchive games — hiding them from the main list without deleting.

**Architecture:** Boolean column on Game model, query param filter on list endpoint, PATCH to toggle, frontend toggle on Games page and archive button on Game Detail.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic, React 19, TypeScript, shadcn v4, TanStack Query, lucide-react.

## Global Constraints

- API follows JSON:API 1.1 (see `backend/CLAUDE.md`)
- Resource objects use `uid` (never expose internal `id`)
- One endpoint per file under `backend/app/routers/<resource>/`
- Frontend imports use `@/` path alias
- Tests use SQLite in-memory via `backend/tests/conftest.py`

---

### Task 1: Backend — Model + Migration + PATCH Endpoint + List Filter

**Files:**
- Modify: `open_hoops/db/models.py` (add `is_archived` column)
- Create: `backend/alembic/versions/xxxx_add_game_is_archived.py` (migration)
- Modify: `backend/app/routers/games/serialize.py` (include `is_archived`)
- Modify: `backend/app/routers/games/collection.py` (add `archived` query param)
- Create: `backend/app/routers/games/patch.py` (PATCH handler)
- Modify: `backend/app/routers/games/router.py` (register PATCH)
- Test: `backend/tests/test_games_api.py` (add archive tests)

**Interfaces:**
- Produces: `PATCH /api/games/{uid}` accepting `{ "data": { "type": "games", "uid": "...", "attributes": { "is_archived": true } } }`
- Produces: `GET /api/games?archived=true|false` filter (default false)
- Produces: `is_archived` field in all game serialization

- [ ] **Step 1: Add `is_archived` column to Game model**

In `open_hoops/db/models.py`, add after the `status` field:

```python
is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
```

Add `Boolean` to the imports from `sqlalchemy`.

- [ ] **Step 2: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add game is_archived column"
```

Verify the generated migration has `op.add_column('games', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))` in upgrade and `op.drop_column('games', 'is_archived')` in downgrade.

- [ ] **Step 3: Add `is_archived` to serialization**

In `backend/app/routers/games/serialize.py`, add to the `attributes` dict in `serialize_game`:

```python
"is_archived": game.is_archived,
```

(After the `"file_count"` line.)

- [ ] **Step 4: Add `archived` filter to collection endpoint**

Rewrite `backend/app/routers/games/collection.py`:

```python
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game
from .serialize import serialize_game


def list_games(archived: bool = Query(False), db: Session = Depends(get_db)):
    query = db.query(Game).filter(Game.is_archived == archived).order_by(Game.date.desc())
    games = query.all()
    return document(
        data=[serialize_game(g) for g in games],
        meta={"count": len(games)},
    )
```

- [ ] **Step 5: Create PATCH endpoint**

Create `backend/app/routers/games/patch.py`:

```python
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game
from .serialize import serialize_game

ALLOWED_ATTRS = {"is_archived"}


def update_game(uid: str, body: dict, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")
    attrs = body.get("data", {}).get("attributes", {})
    for key, value in attrs.items():
        if key in ALLOWED_ATTRS and hasattr(game, key):
            setattr(game, key, value)
    db.commit()
    db.refresh(game)
    return document(data=serialize_game(game))
```

- [ ] **Step 6: Register PATCH in router**

Modify `backend/app/routers/games/router.py`:

```python
from fastapi import APIRouter

from .collection import list_games
from .post import upload_game
from .get import get_game
from .patch import update_game
from .stats import get_game_stats, get_game_events
from .files import list_game_files

router = APIRouter(prefix="/api/games", tags=["games"])
router.get("")(list_games)
router.post("")(upload_game)
router.get("/{uid}")(get_game)
router.patch("/{uid}")(update_game)
router.get("/{uid}/stats")(get_game_stats)
router.get("/{uid}/events")(get_game_events)
router.get("/{uid}/files")(list_game_files)
```

- [ ] **Step 7: Write tests**

Add to `backend/tests/test_games_api.py`:

```python
@patch("app.routers.games.post.celery_app.send_task")
def test_archive_game(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.return_value = None

    resp = client.post(
        "/api/games",
        data={
            "name": "G1",
            "date": "2026-01-15",
            "own_team_uid": home_uid,
            "opponent_team_uid": away_uid,
        },
        files=[("files", ("g.mp4", BytesIO(b"data"), "video/mp4"))],
    )
    uid = resp.json()["data"]["uid"]

    # Archive it
    resp = client.patch(
        f"/api/games/{uid}",
        json={"data": {"type": "games", "uid": uid, "attributes": {"is_archived": True}}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["is_archived"] is True

    # Archived game hidden from default list
    resp = client.get("/api/games")
    assert len(resp.json()["data"]) == 0

    # Visible with archived=true
    resp = client.get("/api/games?archived=true")
    assert len(resp.json()["data"]) == 1

    # Unarchive
    resp = client.patch(
        f"/api/games/{uid}",
        json={"data": {"type": "games", "uid": uid, "attributes": {"is_archived": False}}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["is_archived"] is False

    # Back in default list
    resp = client.get("/api/games")
    assert len(resp.json()["data"]) == 1


def test_patch_game_not_found():
    resp = client.patch(
        "/api/games/doesnotexist",
        json={"data": {"type": "games", "uid": "doesnotexist", "attributes": {"is_archived": True}}},
    )
    assert resp.status_code == 404
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_games_api.py -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add open_hoops/db/models.py backend/app/routers/games/ backend/alembic/versions/ backend/tests/test_games_api.py
git commit -m "feat: game archiving backend — model, PATCH endpoint, list filter"
```

---

### Task 2: Frontend — Archive/Unarchive on Game Detail + Toggle on Games Page

**Files:**
- Modify: `frontend/src/lib/api.ts` (add `archived` param to list, add `updateGame` method, add `is_archived` to Game type)
- Modify: `frontend/src/pages/GameDetail.tsx` (archive/unarchive button)
- Modify: `frontend/src/pages/Games.tsx` (show archived toggle, badge on archived games)

**Interfaces:**
- Consumes: `PATCH /api/games/{uid}` from Task 1, `GET /api/games?archived=` from Task 1
- Produces: `gamesApi.list(archived?: boolean)`, `gamesApi.update(uid, attrs)` in frontend API layer

- [ ] **Step 1: Update Game type and API layer**

In `frontend/src/lib/api.ts`, add `is_archived` to the `Game` interface:

```typescript
export interface Game {
  uid: string;
  name: string;
  date: string;
  status: "pending" | "processing" | "done" | "failed";
  own_team_uid: string;
  opponent_team_uid: string;
  own_team_color: string;
  opponent_team_color: string;
  duration_seconds: number;
  fps: number;
  file_count: number;
  is_archived: boolean;
}
```

Update `gamesApi.list` to accept optional archived param:

```typescript
list: async (archived?: boolean): Promise<Game[]> => {
  const params: Record<string, string> = {};
  if (archived !== undefined) params.archived = String(archived);
  const { data } = await client.get("/games", { params });
  return extractManyWithRels(data) as unknown as Game[];
},
```

Add `update` method to `gamesApi`:

```typescript
update: async (uid: string, attrs: Partial<Pick<Game, "is_archived">>): Promise<Game> => {
  const { data } = await client.patch(`/games/${uid}`, {
    data: { type: "games", uid, attributes: attrs },
  });
  return extractOneWithRels(data) as unknown as Game;
},
```

- [ ] **Step 2: Add archive button to GameDetail.tsx**

Add imports:

```typescript
import { Archive, ArchiveRestore } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
```

(Some may already be imported — just add the missing ones: `Archive`, `ArchiveRestore`, `useMutation`, `toast`.)

Inside `GameDetail`, after the existing queries, add the mutation:

```typescript
const queryClient = useQueryClient();

const archiveMutation = useMutation({
  mutationFn: (archived: boolean) => gamesApi.update(uid!, { is_archived: archived }),
  onSuccess: (updated) => {
    queryClient.invalidateQueries({ queryKey: ["game", uid] });
    queryClient.invalidateQueries({ queryKey: ["games"] });
    toast(updated.is_archived ? "Game archived" : "Game restored");
  },
});
```

In the rendered header area (after the `<h1>` tag), add the button:

```tsx
<div className="flex items-center gap-4">
  <h1 className="text-2xl font-bold">{game.name}</h1>
  {game.status === "done" && (
    <Button
      variant={game.is_archived ? "outline" : "ghost"}
      size="sm"
      onClick={() => archiveMutation.mutate(!game.is_archived)}
      disabled={archiveMutation.isPending}
    >
      {game.is_archived ? (
        <><ArchiveRestore className="h-4 w-4 mr-1" /> Unarchive</>
      ) : (
        <><Archive className="h-4 w-4 mr-1" /> Archive</>
      )}
    </Button>
  )}
</div>
```

Replace the existing bare `<h1 className="text-2xl font-bold">{game.name}</h1>` with the `<div>` above.

- [ ] **Step 3: Add archived toggle and badge to Games.tsx**

Add state for the toggle at top of `Games` component:

```typescript
const [showArchived, setShowArchived] = useState(false);
```

Update the games query to pass the param:

```typescript
const { data: games } = useQuery({
  queryKey: ["games", { archived: showArchived }],
  queryFn: () => gamesApi.list(showArchived || undefined),
  refetchInterval: showArchived ? false : 5000,
});
```

Add a toggle button above the Games card (between the upload card and games card):

```tsx
<div className="flex items-center gap-2">
  <Button
    variant={showArchived ? "default" : "outline"}
    size="sm"
    onClick={() => setShowArchived(!showArchived)}
  >
    <Archive className="h-4 w-4 mr-1" />
    {showArchived ? "Showing archived" : "Show archived"}
  </Button>
</div>
```

Add `Archive` to the lucide imports.

In the table rows, if a game is archived, show a badge:

```tsx
<TableCell>
  <Badge className={STATUS_COLORS[v.status]}>{v.status}</Badge>
  {v.is_archived && <Badge variant="outline" className="ml-1">Archived</Badge>}
</TableCell>
```

- [ ] **Step 4: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/GameDetail.tsx frontend/src/pages/Games.tsx
git commit -m "feat(frontend): game archive/unarchive UI with toggle and detail button"
```

---
