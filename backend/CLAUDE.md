# Backend — JSON:API 1.1

All API responses follow the [JSON:API 1.1 specification](https://jsonapi.org/format/1.1/).

## Response Envelope

Every response wraps data in the standard document structure:

```json
{
  "data": { "type": "teams", "uid": "<uid>", "attributes": {...} },
  "meta": {},
  "jsonapi": { "version": "1.1" }
}
```

- `data` — single resource object or array of resource objects.
- `type` — plural resource name matching the DB table name (teams, players, games).
- `uid` — 32-char hex string. Intentional deviation from JSON:API `id`: we use the field name `uid` in resource objects to make explicit this is NOT the internal database primary key. Never expose the auto-increment `id`.

## Attributes vs Relationships

Scalar fields go in `attributes`. Foreign keys become `relationships` with resource linkage:

```json
{
  "data": {
    "type": "players",
    "uid": "abc123...",
    "attributes": { "jersey_number": 23, "name": "Jordan" },
    "relationships": {
      "team": { "data": { "type": "teams", "uid": "def456..." } }
    }
  }
}
```

Never put `type` or `uid` inside `attributes`.

## Collection Responses

```json
{
  "data": [
    { "type": "teams", "uid": "...", "attributes": {...} }
  ],
  "meta": { "count": 2 }
}
```

Include `meta.count` for list endpoints.

## Creating Resources (POST)

Request body uses the same envelope:

```json
{
  "data": {
    "type": "teams",
    "attributes": { "name": "Bulls", "is_own": true, "home_color": "#CE1141" }
  }
}
```

Client MUST NOT provide `id` on create — server generates it.

## Updating Resources (PATCH)

JSON:API uses PATCH (not PUT) for partial updates. Request includes only changed fields:

```json
{
  "data": {
    "type": "teams",
    "uid": "<uid>",
    "attributes": { "home_color": "#000000" }
  }
}
```

## Errors

Error responses use the `errors` array, never `data`:

```json
{
  "errors": [
    {
      "status": "404",
      "title": "Not Found",
      "detail": "Team not found"
    }
  ]
}
```

Status codes as strings. One error object per problem.

## Content-Type

All requests and responses use:
```
Content-Type: application/vnd.api+json
```

## Pagination

Cursor-based pagination using `page[after]` and `page[size]`:
- `GET /api/games?page[size]=20&page[after]=<uid>`
- Default page size: 20. Max: 100.
- Response `meta` includes: `{ "count": 42, "page_size": 20, "has_next": true }`
- `links.next` included when `has_next` is true.

## Sorting

Use `sort` query param. Prefix with `-` for descending:
- `GET /api/games?sort=-date`
- `GET /api/players?sort=jersey_number`
- Multiple: `?sort=-date,name`

## Filtering

Use plain query params (no JSON:API `filter[]` bracket syntax):
- `GET /api/teams?is_own=true`
- `GET /api/players?team=<team_uid>`

## Sparse Fieldsets / Includes

Use `include` query param to specify which fields or relationships to return:
- `GET /api/teams?include=name,home_color` — only return listed attributes
- `GET /api/games/abc123?include=home_team,away_team` — sideload related resources

When including relationships, response adds `included` array:
```json
{
  "data": { "type": "games", "uid": "...", ... },
  "included": [
    { "type": "teams", "uid": "...", "attributes": {...} }
  ]
}
```

## HTTP Status Codes

| Action | Success | Notes |
|--------|---------|-------|
| GET (single) | 200 | |
| GET (list) | 200 | |
| POST | 201 | Returns created resource |
| PATCH | 200 | Returns updated resource |
| DELETE | 204 | Empty body |

## Validation Errors

Field-level validation errors use `source.pointer` to identify the offending field:

```json
{
  "errors": [
    {
      "status": "422",
      "title": "Validation Error",
      "detail": "Name is required",
      "source": { "pointer": "/data/attributes/name" }
    }
  ]
}
```

Return 422 for request body validation failures. Return 400 for malformed JSON or missing envelope.

## Date/Time Format

- All dates/times in ISO 8601 format.
- Always UTC. Suffix with `Z` (e.g. `"2026-08-04T14:30:00Z"`).
- Date-only fields use `YYYY-MM-DD` (e.g. `"2026-08-04"`).

## Null Relationships

When a relationship exists but has no value, represent as null data:
```json
{ "team": { "data": null } }
```

Omit the relationship key entirely only if the relationship doesn't exist on that resource type.

## Naming Conventions

- Attribute names: `snake_case` (matches Python/DB column naming).
- Resource types: plural, lowercase (teams, players, games).
- Relationship keys: singular for to-one (`team`), plural for to-many (`players`).

---

## Development Standards

### One Endpoint Per File

Each API endpoint lives in its own file under `app/routers/<resource>/`:

```
app/routers/
  teams/
    collection.py    # GET /api/teams
    post.py          # POST /api/teams
    get.py           # GET /api/teams/{uid}
    patch.py         # PATCH /api/teams/{uid}
    delete.py        # DELETE /api/teams/{uid}
  players/
    collection.py
    post.py
    get.py
    patch.py
    delete.py
  games/
    ...
```

Each file exports a single handler function (not a router). `__init__.py` is empty. `router.py` registers all handlers on one router:

```python
# app/routers/teams/router.py
from fastapi import APIRouter

from .collection import list_teams
from .post import create_team
from .get import get_team
from .patch import update_team
from .delete import delete_team

router = APIRouter(prefix="/api/teams", tags=["teams"])
router.get("")(list_teams)
router.post("")(create_team)
router.get("/{uid}")(get_team)
router.patch("/{uid}")(update_team)
router.delete("/{uid}")(delete_team)
```

### File Naming

- `collection.py` — list endpoint (GET collection)
- `get.py` — single resource (GET by uid)
- `post.py` — create
- `patch.py` — partial update
- `delete.py` — delete

## Implementation Notes

- Pydantic schemas model the JSON:API document structure, not flat DB rows.
- Use a shared `JsonApiDocument` / `ResourceObject` base schema to enforce envelope shape.
- Router serialization converts SQLAlchemy models → JSON:API resource objects.
- Resource objects use `uid` (not `id`) as identifier field. Internal `id` column never appears in responses.
- Relationship linkage uses UIDs resolved via the ORM relationship, not raw FK ints.
