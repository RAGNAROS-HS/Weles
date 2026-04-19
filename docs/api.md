# API Reference

> Keep this document current. Update it when any issue adds, removes, or changes an endpoint.

Base URL (dev): `http://localhost:8000`

---

## Health

### `GET /health`
Returns app state flags.

**Response `200`**
```json
{
  "status": "ok",
  "web_search": true,
  "first_run": false
}
```

- `web_search`: false when `TAVILY_API_KEY` is absent
- `first_run`: true when `profile.first_session_at IS NULL`

---

## Sessions

### `POST /sessions`
Create a new chat session. Runs session-start checks.

**Response `201`**
```json
{
  "id": "uuid",
  "title": null,
  "mode": "general",
  "created_at": "ISO datetime",
  "session_start_prompt": null
}
```

- `title`: null until first user message is saved (set to first 50 chars)
- `session_start_prompt`: null until Issue #24 (orchestrator) is implemented; field present from Issue #5

### `GET /sessions`
List all sessions, most recent first.

**Query params** (optional):
- `search`: substring match on `title` (case-insensitive); sessions with `null` title are excluded from search results

**Response `200`** — array of:
```json
{
  "id": "uuid",
  "title": "string or null",
  "mode": "general|shopping|diet|fitness|lifestyle",
  "created_at": "ISO datetime",
  "preview": "first 60 chars of first user message, or null"
}
```

### `PATCH /sessions/{id}`
Update session title or mode.

**Request body** (all fields optional):
```json
{ "title": "string", "mode": "shopping" }
```

**Response `200`** — updated session object

**Errors:** `404` session not found; `422` invalid mode

### `DELETE /sessions/{id}`
Delete session and all its messages (cascade).

**Response `204`**

---

## Messages

### `POST /sessions/{id}/messages`
Send a message. Returns SSE stream.

**Request body:**
```json
{ "content": "string" }
```

**Response `200`** — `Content-Type: text/event-stream`

SSE event types:
```
event: text_delta     data: {"delta": "..."}
event: tool_start     data: {"tool": "search_reddit", "description": "Searching r/BuyItForLife..."}
event: tool_end       data: {"tool": "search_reddit", "result_summary": "Found 8 posts"}
event: tool_error     data: {"tool": "search_reddit", "error": "Request timed out"}
event: done           data: {"session_id": "uuid", "title": "string"}
event: error          data: {"message": "Claude API unavailable"}
```

`tool_error` is non-fatal — stream continues. `error` terminates the stream.

### `GET /sessions/{id}/messages`
Retrieve paginated message history for a session.

**Query params** (all optional):
- `limit`: max messages to return (default `100`)
- `before_id`: cursor — return up to `limit` messages with `created_at` before this message ID, in chronological order

**Response `200`** — array of:
```json
{
  "id": "uuid",
  "session_id": "uuid",
  "role": "user|assistant|tool_result",
  "content": "string",
  "tool_name": "string or null",
  "is_compressed": false,
  "created_at": "ISO datetime"
}
```

When `before_id` is not provided: returns the last `limit` messages chronologically.
When `before_id` is provided: returns up to `limit` messages preceding that message ID.

---

## Profile

### `GET /profile`
Return full user profile. All nullable fields included (not omitted).

**Response `200`** — `UserProfile` object (all fields, nulls included)

### `PATCH /profile`
Partial update. Updates `field_timestamps` atomically with each changed field.

**Request body** — any subset of profile fields:
```json
{
  "fitness_level": "beginner",
  "weight_kg": 80.0,
  "dietary_restrictions": ["gluten"]
}
```

**Response `200`** — updated profile

**Errors:** `422` unknown field name; `422` invalid enum value

---

## History

### `GET /history`
List history items, most recent first, with pagination.

**Query params** (all optional):
- `domain`: `shopping|diet|fitness|lifestyle`
- `status`: `recommended|bought|tried|rated|skipped`
- `search`: substring match on `item_name` (case-insensitive)
- `sort`: `newest` (default) | `oldest` — controls `created_at` sort order
- `limit`: items per page (default `50`)
- `offset`: number of items to skip (default `0`)

**Response `200`**:
```json
{
  "items": [...],
  "total": 75,
  "limit": 50,
  "offset": 0
}
```

### `DELETE /history/{id}`
Delete a history item.

**Response `204`**

---

## Preferences

### `GET /preferences`
List all learned preferences, oldest first.

**Response `200`** — array of:
```json
{
  "id": "uuid",
  "dimension": "string",
  "value": "string",
  "reason": "string or null",
  "source": "string",
  "created_at": "ISO datetime or null"
}
```

### `DELETE /preferences/{id}`
Delete a learned preference. Agent reverts to prior behaviour for that dimension.

**Response `204`**

---

## Settings

### `GET /settings`
Return all settings as a flat key-value map.

**Response `200`**
```json
{
  "follow_up_cadence": "off",
  "proactive_surfacing": "true",
  "decay_thresholds": {"goals": 60, "fitness_level": 90, "dietary_approach": 90, "body_metrics": 180, "taste_lifestyle": 365},
  "max_tool_calls_per_turn": "6"
}
```

### `PATCH /settings`
Partial update. Rejects unknown keys.

**Request body** — any subset of known settings keys

**Response `200`** — updated settings map

**Errors:** `422` unknown key

---

## Data

### `DELETE /data`
Wipe all user data. Runs `alembic downgrade base` then `alembic upgrade head`.

**Response `204`**

Used by the Settings page "Clear all data" button.
