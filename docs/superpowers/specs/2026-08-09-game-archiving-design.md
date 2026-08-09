# Game Archiving Design Spec

Hide games from the main list without deleting them. Restorable.

## Backend

### Model Change
- Add `is_archived: bool` column to `Game` model, default `False`, not nullable.
- Alembic migration for the column.

### API Changes

**GET /api/games**
- New query param: `archived` (boolean string, default `"false"`)
- `archived=false` → only non-archived games (default behavior)
- `archived=true` → only archived games
- Omitted → same as `false`

**PATCH /api/games/{uid}**
- Accept `is_archived` in attributes. No new endpoint needed.

**Serialization**
- Include `is_archived` in game resource attributes.

## Frontend

### Games Page
- Toggle above the games table: "Show archived" (off by default)
- When toggled on: re-fetch with `?archived=true`
- Archived games show an "Archived" badge in status column (or alongside status)
- Active toggle state reflected in query key so TanStack Query caches separately

### Game Detail Page
- Archive/Unarchive button in header next to game title
- Non-archived: "Archive" button (ghost variant, Archive lucide icon)
- Archived: "Unarchive" button (outline variant, ArchiveRestore lucide icon)
- On click: PATCH `is_archived` → invalidate game + games queries → toast feedback
- Toast messages: "Game archived" / "Game restored"
- Stay on page after action (no navigation)

### Dashboard
- No change needed — dashboard already uses `gamesApi.list()` which will default to `archived=false`
- Update `gamesApi.list()` to accept optional `archived` param, default undefined (backend defaults to false)

## Data Flow

1. User clicks "Archive" on detail page
2. Frontend PATCHes `/api/games/{uid}` with `{ is_archived: true }`
3. Backend updates row, returns updated game
4. Frontend invalidates `["games"]` and `["game", uid]` queries
5. Toast shows "Game archived"
6. Game disappears from main list (but still visible on current detail page)
7. On Games page, user can toggle "Show archived" to see archived games
8. From archived view or detail page, user can click "Unarchive" to restore
