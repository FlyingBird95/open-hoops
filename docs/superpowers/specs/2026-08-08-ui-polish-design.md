# UI Polish Design Spec

Clean/minimal sport aesthetic. Component-by-component approach — each enhancement independent and shippable.

## 1. App Shell — Collapsible Sidebar + Dark Mode

### Sidebar
- Collapsible: ~60px collapsed (icon-only), ~220px expanded (icon + label).
- Toggle button at top.
- Nav items: Dashboard (Home icon), My Team (Users), Opponents (Shield), Games (Video).
- Bottom: dark mode toggle (Sun/Moon icon).
- Top: basketball icon + "Open Hoops" text (hidden when collapsed).
- Use shadcn `sidebar` primitive (CSS vars already in index.css).

### Dark Mode
- Toggle adds/removes `.dark` class on `<html>`.
- Persist in `localStorage`.
- Default: `prefers-color-scheme` media query.

### Route Change
- `/` → Dashboard (new)
- `/my-team` → My Team (moved from `/`)
- `/opponents` → Opponents (unchanged)
- `/games` → Games (unchanged)
- `/games/:uid` → Game Detail (unchanged)

## 2. Dashboard (Activity-focused)

Route: `/`

### Stat Tiles (top row)
- Games processed (count of `done`)
- Currently processing (count of `processing` + `pending`, pulse animation if >0)
- Total footage (sum of `duration_seconds`, formatted as hours)

### Active Jobs (middle)
- Cards for games with status `processing` or `pending`
- Game name, opponent, animated spinner/pulse
- Click → game detail

### Recent Completions (bottom)
- Last 5 games with status `done`
- Game name, date, score, opponent, "done" badge
- Click → game detail

### Empty State
- When no games exist: large icon + "Upload your first game" + CTA to Games page

### Data Source
- `gamesApi.list()` — no new endpoints.

## 3. Empty States

Pattern applied to: Dashboard, Roster, Opponents, Games list.

- Centered in content area
- Large muted lucide icon (contextual)
- Short heading + one-line description
- CTA button where applicable

Icons:
- Dashboard: `PlayCircle`
- Roster: `UserPlus`
- Opponents: `ShieldPlus`
- Games: `Upload`

## 4. Loading Skeletons

- Replace "Loading..." with shimmer skeletons matching content shape.
- Use shadcn `Skeleton` component.
- Inline per page (no shared abstraction).

Locations:
- Dashboard stat tiles → 3 rect blocks
- Active/recent game cards → 3-5 card skeletons
- Games table → 5 row skeletons
- Player roster → 3 row skeletons
- Game detail → scoreboard skeleton + table row skeletons

Triggered by `isLoading` from TanStack Query.

## 5. Game Detail — Full Data Viz

### Scoreboard Matchup Card
- Large centered: `Team A  72 — 68  Team B`
- Team color indicators on each side
- Possession bar underneath (horizontal stacked bar, proportional %)

### Player Stats Table (enhanced)
- Grouped by team (two sections, team color header bar)
- Columns: #, Shots, Makes, FG%, Passes, Distance
- FG% → inline horizontal bar (team-colored, proportional)
- Distance → mini bar relative to max in game
- Top performer per stat highlighted (bold/subtle bg)

### Shot Donut Charts
- Per-team small ring chart: makes vs misses
- Beside scoreboard or in team section header

### Possession Timeline (stretch)
- Horizontal bar showing possession over time, colored by team
- Only if events data supports it

### Event Timeline (style pass)
- Better icons per event type
- Team-colored left border

## 6. Upload UX

### Drag-and-Drop Zone
- Replaces plain file input
- Dashed border, centered `Upload` icon, "Drag videos here or click to browse"
- Highlight on drag-over (border color + bg tint)
- File list below: filename, size, remove button per file

### Upload Progress
- Progress bar via axios `onUploadProgress`
- Form disabled during upload
- On success: toast + clear form

### Form Visual Grouping
- Three sections within card (not wizard):
  1. Game info (name + date)
  2. Teams (my team + opponent + jersey colors)
  3. Files (drop zone)
- Each section with subtle separator

## 7. Toast Notifications

Library: `sonner` via shadcn integration.

Triggers:
- Upload success/error
- Player added/removed
- Team created/updated
- Opponent created/deleted

Position: bottom-right. Auto-dismiss 4s. Errors persist until dismissed.

## 8. Dependencies

### shadcn components to install:
- `sidebar`
- `skeleton`
- `sonner`
- `progress`
- `separator`
- `tooltip`

### NPM packages:
- `sonner`

### No charting library
- FG% bars, donuts, possession bar → raw SVG + Tailwind
- Keeps bundle small

### No new backend endpoints
- All data from existing API
