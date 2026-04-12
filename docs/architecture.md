# Architecture

> Keep this document current. Update it when any issue changes a core pattern, data flow, or module boundary.

---

## Overview

Weles is a single-user, locally-hosted AI agent. FastAPI serves both the API and the built React frontend from a single process. In production (and as a `.exe`) there is no Node.js process — the frontend is a static build mounted at `/`.

```
Browser  ←→  FastAPI (uvicorn)  ←→  Claude API
                  |
               SQLite
            (~/.weles/weles.db)
```

---

## Request lifecycle — chat message

1. `POST /sessions/{id}/messages` received with `{content, mode}`
2. **Session start checks** run on first message only (via `run_session_start_checks`)
3. `first_session_at` written to `profile` if null (first-ever message)
4. `Session.get_messages_for_context()` assembles history (compressed messages substituted)
5. `build_system_prompt(mode, profile, preferences)` builds the Anthropic `system` array:
   - Block 1: `prompts/system.md` (always)
   - Block 2: `prompts/modes/{mode}.md` (if mode ≠ general)
   - Block 3: serialised profile + preferences (if non-empty)
6. Missing profile fields for this mode appended to user turn as `[System: ...]` note
7. History context for this domain appended to user turn
8. `stream_response(client, messages, tools, system)` called → yields `AgentEvent`s
9. Each `AgentEvent` serialised to SSE and flushed to browser immediately
10. Tool calls dispatched via `ToolRegistry.dispatch()`; `max_tool_calls_per_turn` enforced
11. On turn completion: tool results compressed async (fire-and-forget); session saved to DB

---

## Module map

| Module | Responsibility |
|---|---|
| `agent/client.py` | `get_client() -> Anthropic`; wraps client with `wrap_anthropic` for LangSmith tracing |
| `agent/stream.py` | `stream_response()` → `AsyncIterator[AgentEvent]`; `@traceable` parent span for the full agent loop |
| `agent/dispatch.py` | `ToolRegistry`: register, dispatch, schema export; enforces tool call cap; `adispatch` is `@traceable(run_type="tool")` |
| `agent/session.py` | `Session`: message list, compression, token estimation |
| `agent/prompts.py` | `build_system_prompt(mode, profile, preferences)` |
| `agent/context.py` | `check_missing_fields(mode, profile)` |
| `api/main.py` | FastAPI app; lifespan wires `startup()`; mounts `frontend/dist/` in production |
| `api/startup.py` | `startup()`: env validation, DB migration, app state flags |
| `api/session_start.py` | `run_session_start_checks()` orchestrator + individual check functions |
| `api/routers/` | One router per resource group (sessions, profile, history, settings, data) |
| `db/connection.py` | `get_db()`: WAL-mode SQLite connection, cached per thread |
| `db/profile_repo.py` | `get_profile()`, `update_profile()`, `get_preferences()` |
| `db/history_repo.py` | `add_to_history()`, `get_history_context()`, `get_history()` |
| `db/settings_repo.py` | `get_setting()`, `set_setting()`, `get_all_settings()` |
| `profile/models.py` | `UserProfile` Pydantic model; all enums |
| `profile/context.py` | `build_profile_block()` → serialised string for system prompt |
| `profile/decay.py` | `check_decay()` → stale field detection |
| `research/credibility.py` | `score_result()` → `CredibilityLabel`; affiliate + astroturf detection |
| `research/routing.py` | `get_subreddits(mode, subcategory)` from `config/subreddits.toml` |
| `tools/reddit.py` | `search_reddit()` tool; httpx → Reddit public JSON API |
| `tools/web.py` | `search_web()` tool; Tavily API; only registered when key present |
| `tools/history_tools.py` | `add_to_history()` Claude tool |
| `tools/profile_tools.py` | `save_profile_field()`, `update_preference()` Claude tools |
| `utils/paths.py` | `resource_path()`: PyInstaller-safe file path resolution |
| `utils/errors.py` | `ConfigurationError`, `ToolNotFoundError`, `RedditUnavailableError`, `MaxToolCallsError` |
| `tray.py` | pystray system tray; starts uvicorn in daemon thread; Windows auto-start (#32) |

---

## Database schema

Six tables. All created in one Alembic migration (`001_initial.py`). Never add columns mid-project — extend `001_initial.py` or add a new migration.

| Table | Purpose |
|---|---|
| `sessions` | Chat sessions: id, title, mode, created_at |
| `messages` | All messages: role, content, tool_name, is_compressed |
| `profile` | Single row (id=1): all user profile fields + field_timestamps JSON |
| `history` | Items recommended/bought/tried: follow_up_due_at, check_in_due_at |
| `preferences` | Learned preferences: dimension, value, source (user_explicit / agent_inferred) |
| `settings` | Key-value store: follow_up_cadence, proactive_surfacing, decay_thresholds, max_tool_calls_per_turn |

---

## Agent event types

All yielded by `stream.py`, serialised to SSE by the router:

```
text_delta    {"delta": "..."}
tool_start    {"tool": "...", "description": "..."}
tool_end      {"tool": "...", "result_summary": "..."}
tool_error    {"tool": "...", "error": "..."}
done          {"session_id": "...", "title": "..."}
error         {"message": "..."}
```

`tool_error` never aborts the stream. `error` (Claude API failure) does.

---

## Session start orchestrator

`run_session_start_checks(db)` runs once per new session, in this exact order:

1. Passive pattern detection — silent; writes `agent_inferred` preferences; no user prompt
2. Profile decay check — if stale field found, sets `prompt`
3. Follow-up check — if overdue follow-up AND no prompt yet, sets `prompt`
4. Check-in check — if overdue check-in AND no prompt yet, sets `prompt`
5. QC / proactive surfacing — always runs; adds to `notices` list regardless of prompt

At most one `prompt` surfaces per session. `notices` are independent (shown as dismissable banners).

---

## PyInstaller constraints

- **`resource_path(relative)`** must be used for every file read of config, prompts, blocklists, assets. It returns `Path(sys._MEIPASS) / relative` when frozen, else repo root.
- `multiprocessing.freeze_support()` called at top of `tray.py` before any imports.
- Frontend served as `StaticFiles` from `frontend/dist/` (bundled into the `.exe`).
- API keys live in `~/.weles/.env` — never bundled.

---

## LangSmith tracing

Enabled when `LANGSMITH_TRACING=true`. Three layers:

| Layer | What it traces |
|---|---|
| `wrap_anthropic(client)` in `client.py` | Every Claude API call: model, inputs, outputs, token usage, latency |
| `@traceable(run_type="chain")` on `stream_response` | Full agent loop as a parent span, including multi-turn tool-use cycles |
| `@traceable(run_type="tool")` on `adispatch` | Each individual tool dispatch: name, input, result |

Set `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com` for EU-region accounts.

`stream_response` must exhaust naturally (no early `break` on `DoneEvent` in the consumer) — closing the generator mid-flight throws `GeneratorExit`, which LangSmith logs as an error.

---

## Key invariants

| Invariant | Where enforced |
|---|---|
| `first_session_at` written on first-ever message | `api/routers/messages.py` |
| At most 1 user-facing prompt per session start | `session_start.py` orchestrator |
| Tool calls capped at `max_tool_calls_per_turn` (default 6) | `agent/dispatch.py` |
| Tool errors never abort SSE stream | `agent/dispatch.py` |
| Last 10 messages never compressed | `agent/session.py` |
| All file reads use `resource_path` | `utils/paths.py` |
| `stream_response` must be consumed to exhaustion | `api/routers/messages.py` |
