# Changelog

All notable changes to Weles are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### v0.1 — Skeleton

#### Added
- Project scaffold: directory structure, `pyproject.toml` (uv, ruff, mypy, pytest), Makefile, CI workflow (#1)
- `resource_path()` utility for PyInstaller-safe file resolution (#1)
- Shared test fixtures: `mock_claude`, `tmp_db`, `client` in `tests/conftest.py` (#1)
- React + Vite + TypeScript frontend scaffold under `frontend/` (#1)

- Core Claude streaming integration: `client`, `stream`, `dispatch`, `session`, `prompts` modules (#2)
- `AgentEvent` tagged union: `TextDeltaEvent`, `ToolStartEvent`, `ToolEndEvent`, `ToolErrorEvent`, `DoneEvent` (#2)
- `ToolRegistry` with `register`, `dispatch`, `get_tool_schemas`; raises `ToolNotFoundError` on unknown tool (#2)
- `ConfigurationError` raised by `get_client()` when `ANTHROPIC_API_KEY` is absent (#2)
- Interactive CLI REPL (`uv run weles`) with streaming output and clean `exit`/Ctrl+C handling (#2)
- System prompt loaded from `src/weles/prompts/system.md` via `resource_path` (#2)

- SQLite schema: all 6 tables (`sessions`, `messages`, `profile`, `history`, `preferences`, `settings`) in a single Alembic migration `001_initial` (#3)
- Default `settings` rows seeded by migration: `follow_up_cadence`, `proactive_surfacing`, `decay_thresholds`, `max_tool_calls_per_turn` (#3)
- `get_db()` in `src/weles/db/connection.py`; WAL mode enabled, connection cached per-thread (#3)

- `startup()` coroutine in `src/weles/api/startup.py`; validates env, runs migrations, seeds settings, sets `web_search_available` and `is_first_run` on app state (#4)
- `GET /health` endpoint; returns `{"status": "ok", "web_search": bool, "first_run": bool}` (#4)

- FastAPI app with full REST API: sessions, messages, profile, history, settings, preferences, data endpoints (#5)
- SSE streaming on `POST /sessions/{id}/messages`; typed events: `text_delta`, `tool_start`, `tool_end`, `tool_error`, `done`, `error` (#5)
- React + Vite chat UI: sidebar session list, mode selector pill tabs, streaming markdown rendering, tool-use progress strip, settings page (#5)
- `uv run weles` now starts the FastAPI server; CLI REPL removed (#5)
- `DELETE /data` wipes and recreates all tables via alembic downgrade + upgrade (#5)

### v0.2 — Personalization

#### Added
- `UserProfile` Pydantic model in `src/weles/profile/models.py`; all fields optional with `None` default (#6)
- Profile enums: `Build`, `FitnessLevel`, `AestheticStyle`, `BudgetPsychology`, `ActivityLevel`, `LivingSituation`, `DietaryApproach` (#6)
- `profile_is_empty(profile)` helper; returns `True` when all data fields are `None` (#6)
- `GET /profile` returns full profile with nulls included (#6)
- `PATCH /profile` validates enum values and rejects unknown fields with 422; writes `field_timestamps` atomically (#6)
- `build_system_prompt(mode, profile, preferences)` in `prompts.py`; returns Anthropic system array with up to 3 blocks (#7)
- Mode addendum prompts for `shopping`, `diet`, `fitness`, `lifestyle` in `src/weles/prompts/modes/` (#7)
- Mode selector pill tabs call `PATCH /sessions/{id}` on change; mode applies to all subsequent messages (#7)
- `Preference` Pydantic model and `get_preferences()` in `profile_repo.py` (#8)
- `build_profile_block(profile, preferences)` in `profile/context.py`; serialises non-null fields into a compact `[User Profile]` block; returns `None` when empty (#8)
- Profile + preferences injected as Block 3 of every Claude request; block regenerated fresh on each message (#8)
- Token warning logged when profile block exceeds 500 tokens (#8)
- Settings page with human-readable decay threshold labels, Save button, and permanent-delete confirmation modal (#10)
- `check_missing_fields(mode, profile)` in `agent/context.py`; returns null profile fields relevant to current mode (#11)
- `save_profile_field` Claude tool in `tools/profile_tools.py`; registered in `ToolRegistry` on every request (#11)
- Missing profile fields injected as `[System: ...]` note into user turn before each Claude request; each field asked at most once per session (#11)

### Added (continued)
- `add_to_history` Claude tool: records recommended, bought, tried, rated, and skipped items with domain, category, rating, and notes (#12)
- `follow_up_due_at` auto-set on `status=recommended` based on `follow_up_cadence` setting (weekly = 7d, monthly = 30d, off = null) (#12)
- `check_in_due_at` auto-set on `status=bought/tried`: 30 days for fitness/diet, 90 days for shopping/lifestyle (#12)
- `get_history_context(domain)` in `history_repo.py`; injected as `[History — {Domain}]` block into user turn for mode-specific domains (#12)
- `GET /history?domain=&status=` and `DELETE /history/{id}` endpoints (previously stub, now fully wired) (#12)
- History page in frontend: filterable table by domain and status, per-row delete button (#12)

- Information page: profile fields (inline edit, decay indicator, last-updated date), learned preferences (delete), history summary by domain and status (#9)
- `GET /preferences` endpoint to list all learned preferences (#9)

### v0.3 — Research Engine

#### Added
- `ToolResult(summary, data)` named tuple returned by `ToolRegistry.dispatch()`; `summary` drives `tool_end` SSE, `data` is sent to Claude (#13)
- Agentic tool-use loop in `stream_response`: streams text deltas, then processes `tool_use` blocks, emits `ToolStartEvent`/`ToolEndEvent`/`ToolErrorEvent`, and continues until `end_turn` (#13)
- Human-readable `ToolStartEvent.description` per tool: `search_reddit`, `search_web`, `add_to_history`, `save_profile_field`, and a generic fallback (#13)
- Tool exceptions caught in the loop and emitted as `ToolErrorEvent`; Claude instructed to continue with available data (#13)

- `search_reddit` Claude tool: searches Reddit via public JSON API; no credentials required; supports per-subreddit scoping, deduplication, and top-3 comments (#14)
- Rate limiting: `asyncio.Semaphore(1)` + 1 s sleep after every request; 429 backoff using `Retry-After`; 3 retries before `RedditUnavailableError` (#14)
- Posts with score < 5 excluded; results sorted by score descending (#14)
- `max_tool_calls_per_turn` enforced in `ToolRegistry`: reads from settings (default 6); 7th call in a turn raises `MaxToolCallsError` → `ToolErrorEvent` (#14)

<!-- Issues #15–18 -->

### v0.4 — Domain Modules
<!-- Issues #19–22 -->

### v0.5 — Learning Loop
<!-- Issues #23–28 -->

### v0.6 — Signal Quality
<!-- Issues #29–31 -->

### v1.0 — Distribution
<!-- Issue #32 -->

---

<!--
Entry format per merged issue:

### Added
- `POST /sessions` endpoint; returns session with `session_start_prompt` field (#5)
- Reddit search tool via public JSON API; no credentials required (#14)

### Changed
- Session title now set from first 50 chars of first user message (#5)

### Fixed
- (none yet)

Rules:
- One entry per meaningful change, not one per issue
- Lead with the user-visible effect, not the implementation detail
- Reference the issue number in parentheses
- Group under Added / Changed / Fixed / Removed
- Move entries from [Unreleased] to a versioned section on release
-->
