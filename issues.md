# Weles — GitHub Issues Plan

## Architectural Decisions

| # | Decision | Recommendation | Rationale |
|---|---|---|---|
| A1 | **Interface** | Web app (FastAPI + React/Vite) | Onboarding, information tab, and history browsing need a real UI |
| A2 | **LLM** | Claude API (`claude-sonnet-4-6`) | Best tool_use reliability; fits the research loop |
| A3 | **Agent framework** | Raw Anthropic SDK | Tool surface is small and well-defined; no abstraction needed |
| A4 | **Storage** | SQLite at `~/.weles/weles.db` | Single-user local app; zero-ops |
| A5 | **Reddit access** | `httpx` → Reddit public JSON API (no auth) | App registration restricted post-2023; public `.json` endpoints require no credentials |
| A6 | **Web search** | Tavily | Built for LLM agents; degrades gracefully when key absent |
| A7 | **Migrations** | Alembic, run `upgrade head` at every app startup | Full schema in one initial migration; no surprise mid-project columns |
| A8 | **Streaming** | Server-Sent Events (SSE) with structured event types | Carries token deltas and tool-use progress on one stream |
| A9 | **Domain selection** | Explicit mode selector (Shopping / Diet / Fitness / Lifestyle / General) | Removes intent-classification ambiguity |
| A10 | **Onboarding** | No structured intake; agent asks for missing info mid-conversation | Organic; information tab makes the profile transparent |
| A11 | **Context window** | Compress raw tool results after synthesis; summarise oldest turns if window fills | Tool results are large but short-lived; content preserved via summarisation, never dropped |
| A12 | **Error handling** | Tool failures surface as inline notices; Claude continues with available data | Research is best-effort; Claude API failure is the only hard failure |
| A13 | **Dependency management** | `uv` | Fastest resolver; lockfile support |
| A14 | **Distribution** | `pystray` system tray + PyInstaller `.exe` + Windows startup folder | No Docker, no terminal; starts with Windows; no admin rights required |
| A15 | **Session title** | Truncate first user message to 50 chars | Zero API cost; instant; readable enough for a sidebar label |
| A16 | **Test mocking** | `pytest-mock` for Anthropic SDK; `pytest-httpx` for Reddit and Tavily HTTP | Keeps Claude tests decoupled from wire format; HTTP mocks cover Reddit + Tavily cleanly |

---

## Milestones

| Milestone | Goal | Issues |
|---|---|---|
| **v0.1 Skeleton** | Working browser chat with correct tone, persistent sessions | #1–5 |
| **v0.2 Personalization** | Mode selector, profile, information tab, settings, history | #6–12 |
| **v0.3 Research Engine** | Reddit + web search, credibility, synthesis, error resilience | #13–18 |
| **v0.4 Domain Modules** | Shopping, diet, fitness, lifestyle mode implementations | #19–22 |
| **v0.5 Learning Loop** | Context compression, session-start orchestration, follow-ups, check-ins, correction, decay | #23–28 |
| **v0.6 Signal Quality** | Confidence calibration, anti-bias, proactive surfacing | #29–31 |
| **v1.0 Distribution** | System tray app, PyInstaller `.exe`, Windows auto-start | #32 |

---

## v0.1 — Skeleton

### Issue #1: Project scaffold, directory structure, Makefile, CI, and test infrastructure

**Goal:** A fully structured, linted, testable repository that every subsequent issue builds on — including the test mock strategy so every issue ships consistent tests from day one.

**Acceptance criteria:**
- Python 3.12+ project managed with `uv`; `pyproject.toml` defines all runtime and dev deps
- Linting: `ruff` (format + lint); type checking: `mypy --strict`; test runner: `pytest` + `pytest-asyncio`
- Pre-commit hooks: ruff and mypy on every commit
- GitHub Actions: lint + test on every push and PR to `main`
- The following directory tree committed (files may be empty placeholders):
  ```
  weles/
  ├── src/weles/
  │   ├── __init__.py
  │   ├── __main__.py              # CLI dev scaffold (removed in #5)
  │   ├── agent/                   # client.py, stream.py, dispatch.py, session.py, prompts.py, context.py
  │   ├── api/                     # main.py, routers/, startup.py, session_start.py
  │   ├── db/                      # connection.py, profile_repo.py, history_repo.py, settings_repo.py
  │   ├── profile/                 # models.py, context.py, decay.py
  │   ├── tools/                   # reddit.py, web.py, history_tools.py, profile_tools.py
  │   ├── research/                # credibility.py, routing.py
  │   └── utils/                   # paths.py
  ├── frontend/                    # React + Vite + TypeScript
  ├── config/
  │   ├── subreddits.toml
  │   ├── programs.toml
  │   ├── seasonal.toml
  │   └── geo_blocks/              # per-country domain blocklists (e.g. PL.txt)
  ├── blocklist/
  │   ├── commercial_domains.txt
  │   └── community_domains.txt
  ├── assets/
  │   └── icon.ico
  ├── alembic/
  ├── alembic.ini
  ├── tests/
  │   ├── conftest.py              # shared fixtures (see below)
  │   ├── unit/
  │   └── integration/
  ├── scripts/
  │   ├── eval_research.py
  │   └── eval_confidence.py
  ├── src/weles/prompts/
  │   ├── system.md
  │   ├── research.md
  │   └── modes/
  │       ├── shopping.md
  │       ├── diet.md
  │       ├── fitness.md
  │       └── lifestyle.md
  ├── Makefile
  ├── pyproject.toml
  ├── .env.example
  └── .pre-commit-config.yaml
  ```
- `Makefile` targets:
  - `make dev` — Vite dev server + uvicorn with hot reload (via `concurrently`)
  - `make build` — `npm run build` then FastAPI serves static files
  - `make test` — runs pytest
  - `make lint` — ruff + mypy
  - `make install` — startup shortcut (implemented in #32)
  - `make uninstall` — removes startup shortcut (implemented in #32)
  - `make package` — PyInstaller build (implemented in #32)
- `.env.example`:
  ```
  ANTHROPIC_API_KEY=        # Required.
  TAVILY_API_KEY=           # Optional. Web search disabled if absent.
  WELES_MODEL=claude-sonnet-4-6
  WELES_MAX_TOKENS=4096
  WELES_DB_PATH=            # Defaults to ~/.weles/weles.db
  WELES_PORT=8000
  WELES_ENV=development     # development | production
  ```
- `uv run weles` prints `Weles: configuration OK` and exits cleanly

**Tests shipped with this issue:**
- `tests/conftest.py` defines the project-wide test fixtures:
  ```python
  # Mock Anthropic SDK — returns a single canned text response
  @pytest.fixture
  def mock_claude(mocker) -> MagicMock:
      # patches src.weles.agent.client.get_client
      # stream context manager yields [RawTextDeltaEvent("Test."), RawMessageStopEvent()]

  # Temporary SQLite DB with all migrations applied
  @pytest.fixture
  def tmp_db(tmp_path) -> Path:
      # sets WELES_DB_PATH env var to tmp path
      # runs alembic upgrade head against it

  # FastAPI TestClient wired to tmp_db
  @pytest.fixture
  def client(tmp_db) -> TestClient:
      from fastapi.testclient import TestClient
      from src.weles.api.main import app
      with TestClient(app) as c:
          yield c
  ```
- `tests/unit/test_paths.py`: `resource_path("config/subreddits.toml")` returns a valid path in both normal and frozen (mocked `sys.frozen`) mode
- CI passes with zero tests (empty `tests/unit/.gitkeep`) — tests accumulate per issue

**Technical notes:**
- `src/weles/utils/paths.py`: `resource_path(relative: str) -> Path` returns `Path(sys._MEIPASS) / relative` when `getattr(sys, "frozen", False)` is true, otherwise `Path(__file__).parent.parent.parent / relative`
- All config, prompt, and blocklist file reads across the entire codebase go through `resource_path` — never `open("relative/path")`
- `pytest-mock` and `pytest-httpx` added to dev deps in `pyproject.toml`
- `assets/icon.ico` is a placeholder 1×1 pixel ICO; replaced with real icon in #32

**Dependencies:** none

---

### Issue #2: Core Claude integration and CLI dev scaffold

**Goal:** Wire up the Anthropic SDK, system prompt, and streaming into reusable modules. The CLI is temporary dev scaffolding removed in #5 — but all agent modules built here are permanent.

**Acceptance criteria:**
- `uv run weles` starts an interactive CLI REPL
- Full in-session message history passed to Claude on every turn
- System prompt loaded from `src/weles/prompts/system.md` via `resource_path`; content: "You are Weles. Respond factually and without warmth. No preamble. No trailing summaries. State conclusions directly. When data is limited, say so."
- Responses stream token-by-token to stdout
- `exit` / Ctrl+C exits cleanly
- `ANTHROPIC_API_KEY` missing → print clear error and exit; no traceback
- Model: `WELES_MODEL` env var (default `claude-sonnet-4-6`); max tokens: `WELES_MAX_TOKENS` (default `4096`)
- The following modules implemented as independently importable units:
  - `src/weles/agent/client.py` — `get_client() -> AsyncAnthropic`; reads `ANTHROPIC_API_KEY` from env
  - `src/weles/agent/stream.py` — `stream_response(client, messages, tools, system) -> AsyncIterator[AgentEvent]`; yields typed `TextDeltaEvent | ToolStartEvent | ToolEndEvent | ToolErrorEvent | DoneEvent`
  - `src/weles/agent/dispatch.py` — `ToolRegistry`: `register(name, handler, schema)`, `dispatch(tool_name, tool_input) -> str`, `get_tool_schemas() -> list[dict]`
  - `src/weles/agent/session.py` — `Session`: holds `messages: list[dict]`; `add_message(role, content)`, `get_messages() -> list[dict]`; compression added in #23
  - `src/weles/agent/prompts.py` — `build_system_prompt(mode, profile) -> list[dict]`; returns Anthropic `system` array; profile block added in #8

**Tests shipped with this issue:**
- `tests/unit/test_dispatch.py`:
  - Registering a tool and dispatching by name calls the correct handler
  - Dispatching an unknown tool name raises `ToolNotFoundError`
  - `get_tool_schemas()` returns list with correct `name` and `input_schema` keys
- `tests/unit/test_stream.py` (using `mock_claude` fixture):
  - `stream_response` yields `TextDeltaEvent` for text content
  - `stream_response` yields `DoneEvent` as last event
- `tests/unit/test_client.py`:
  - `get_client()` raises `ConfigurationError` with readable message when `ANTHROPIC_API_KEY` not set

**Technical notes:**
- `AgentEvent` is a tagged union (dataclass per type) in `src/weles/agent/stream.py`
- `build_system_prompt` in this issue returns only the base `system.md` block — mode addendum and profile block added in later issues; the function signature is final
- Tool dispatch is synchronous; async tool handlers wrapped with `asyncio.run` or `await` at the call site

**Dependencies:** #1

---

### Issue #3: SQLite schema — complete initial migration

**Goal:** Commit every table, every column, and all default data in a single Alembic migration so no future issue introduces a surprise schema change.

**Acceptance criteria:**
- Alembic configured; `alembic.ini` database URL reads `WELES_DB_PATH` env var (defaults to `~/.weles/weles.db`)
- Single migration `001_initial.py` creates all tables:

  **`sessions`**
  | column | type | notes |
  |---|---|---|
  | id | UUID PK | |
  | title | TEXT | nullable; set from first 50 chars of first user message |
  | mode | TEXT | `general\|shopping\|diet\|fitness\|lifestyle`; default `general` |
  | created_at | DATETIME | |

  **`messages`**
  | column | type | notes |
  |---|---|---|
  | id | UUID PK | |
  | session_id | UUID FK → sessions | ON DELETE CASCADE |
  | role | TEXT | `user\|assistant\|tool_result` |
  | content | TEXT | |
  | tool_name | TEXT | nullable; populated when role=tool_result |
  | is_compressed | BOOLEAN | default false |
  | created_at | DATETIME | |

  **`profile`** (single row, always id=1, upserted on write)
  | column | type | notes |
  |---|---|---|
  | id | INTEGER PK | always 1 |
  | height_cm | REAL | nullable |
  | weight_kg | REAL | nullable |
  | build | TEXT | nullable; `lean\|athletic\|average\|heavy` |
  | fitness_level | TEXT | nullable; `sedentary\|beginner\|intermediate\|advanced` |
  | injury_history | JSON | nullable; string array |
  | dietary_restrictions | JSON | nullable; string array |
  | dietary_preferences | JSON | nullable; string array |
  | dietary_approach | TEXT | nullable; `keto\|vegan\|omnivore\|carnivore\|flexible` |
  | aesthetic_style | TEXT | nullable; `minimal\|technical\|classic\|mixed` |
  | brand_rejections | JSON | nullable; string array |
  | climate | TEXT | nullable |
  | activity_level | TEXT | nullable; `low\|moderate\|high` |
  | living_situation | TEXT | nullable; `urban\|suburban\|rural` |
  | country | TEXT | nullable; ISO 3166-1 alpha-2 |
  | budget_psychology | TEXT | nullable; `buy_once_buy_right\|good_enough\|context_dependent` |
  | fitness_goal | TEXT | nullable |
  | dietary_goal | TEXT | nullable |
  | lifestyle_focus | TEXT | nullable |
  | first_session_at | DATETIME | nullable; set when user sends their first ever message |
  | field_timestamps | JSON | `{"field_name": "ISO datetime"}`; updated per-field on every write |

  **`history`**
  | column | type | notes |
  |---|---|---|
  | id | UUID PK | |
  | item_name | TEXT | |
  | category | TEXT | free-text subcategory e.g. `footwear`, `supplements`, `running_programs` |
  | domain | TEXT | `shopping\|diet\|fitness\|lifestyle` |
  | status | TEXT | `recommended\|bought\|tried\|rated\|skipped` |
  | rating | INTEGER | nullable; 1–5 |
  | notes | TEXT | nullable |
  | follow_up_due_at | DATETIME | nullable |
  | check_in_due_at | DATETIME | nullable |
  | created_at | DATETIME | |

  **`preferences`**
  | column | type | notes |
  |---|---|---|
  | id | UUID PK | |
  | dimension | TEXT | e.g. `shopping.footwear`, `aesthetic_style` |
  | value | TEXT | |
  | reason | TEXT | nullable |
  | source | TEXT | `user_explicit\|agent_inferred` |
  | created_at | DATETIME | |

  **`settings`**
  | column | type | notes |
  |---|---|---|
  | key | TEXT PK | |
  | value | TEXT | JSON-encoded |

  Default `settings` rows inserted by migration:
  - `follow_up_cadence` → `"off"`
  - `proactive_surfacing` → `"true"`
  - `decay_thresholds` → `{"goals": 60, "fitness_level": 90, "dietary_approach": 90, "body_metrics": 180, "taste_lifestyle": 365}`
  - `max_tool_calls_per_turn` → `"6"`

- `src/weles/db/connection.py`: `get_db() -> sqlite3.Connection` with WAL mode; connection cached per-thread

**Tests shipped with this issue:**
- `tests/integration/test_migration.py` (uses `tmp_db` fixture):
  - Migration applies cleanly to a fresh DB
  - All 6 tables exist after migration
  - `sessions`, `messages`, `profile`, `history`, `preferences`, `settings` tables verified via `sqlite_master`
  - Default settings rows present with correct values
  - Alembic `current` revision matches `001_initial`

**Technical notes:**
- WAL mode: `PRAGMA journal_mode=WAL` on every new connection; safe for the tray app's server thread + any future tooling
- `field_timestamps` is a JSON string column; updated atomically with the field it tracks in the same `UPDATE` statement
- After this issue: `startup.py` (from #4) has a module to import but `lifespan` is not yet wired — the CLI from #2 is still runnable; the DB is created and migrated only when `startup()` is explicitly called, which happens in #5

**Dependencies:** #1

---

### Issue #4: App startup sequence and runtime validation

**Goal:** A single coroutine that owns first-run setup, env validation, migration, and app state initialisation — wired into FastAPI lifespan in #5.

**Acceptance criteria:**
- `startup()` async coroutine in `src/weles/api/startup.py`; performs in order:
  1. Load `~/.weles/.env` if it exists (supplements env vars, does not override shell env)
  2. Validate `ANTHROPIC_API_KEY` present — raise `ConfigurationError` with clear message if missing
  3. Create `~/.weles/` directory if absent
  4. Run `alembic upgrade head` programmatically
  5. Seed default `settings` rows if `settings` table is empty
  6. Check `TAVILY_API_KEY` — if absent, log `[WARN] Tavily key not set — web search disabled`; set `web_search_available = False`
  7. Query `profile.first_session_at IS NULL` — set `is_first_run = True` on app state if result is null
- Port conflict: if `WELES_PORT` already bound, exit with readable message before serving
- `GET /health` returns `{"status": "ok", "web_search": bool, "first_run": bool}`

**Tests shipped with this issue:**
- `tests/unit/test_startup.py`:
  - `startup()` with `ANTHROPIC_API_KEY` unset raises `ConfigurationError` containing "ANTHROPIC_API_KEY"
  - `startup()` with `TAVILY_API_KEY` unset sets `web_search_available = False` on app state
  - `startup()` with `TAVILY_API_KEY` set sets `web_search_available = True`
  - `startup()` creates `~/.weles/` dir if absent (using `tmp_path` fixture)
- Note: after this issue the `startup()` module exists but nothing calls it yet — the CLI from #2 remains the runnable entry point until #5 wires `lifespan`

**Technical notes:**
- `alembic upgrade head` called via: `cfg = alembic.config.Config("alembic.ini"); alembic.command.upgrade(cfg, "head")`
- `ConfigurationError` is a custom exception in `src/weles/utils/errors.py`
- App state carried on `app.state` (FastAPI): `web_search_available: bool`, `is_first_run: bool`

**Dependencies:** #3

---

### Issue #5: FastAPI backend and React chat UI

**Goal:** A working browser-based chat interface that replaces the CLI. Streaming responses, session management, markdown rendering, keyboard shortcuts, tool-use progress display, error states, and a settings page. This is the permanent app shell — every subsequent issue adds features on top of it.

**Acceptance criteria:**

**API endpoints:**
- `POST /sessions` → `{id, title: null, mode: "general", created_at, session_start_prompt: null}`
  - `title` set from first 50 chars of first user message when that message is saved
  - `session_start_prompt` is null until #24 implements the orchestrator; field present from day one
- `GET /sessions` → array of `{id, title, mode, created_at, preview}` (`preview` = first 60 chars of first user message, or null)
- `DELETE /sessions/{id}` → 204; cascades to messages
- `PATCH /sessions/{id}` → accepts `{title?, mode?}`; returns updated session
- `POST /sessions/{id}/messages` → SSE stream
- `GET /sessions/{id}/messages` → full message list
- `GET /profile` → full profile with nulls included
- `PATCH /profile` → partial update; returns updated profile
- `GET /history?domain=&status=` → filtered history
- `DELETE /history/{id}` → 204
- `GET /settings` → `{key: value, ...}` for all settings rows
- `PATCH /settings` → partial update; rejects unknown keys with 422
- `DELETE /preferences/{id}` → 204
- `GET /health` → health + app state flags
- `DELETE /data` → drops and recreates all tables; returns 204 (used by settings "Clear all data")

**SSE event types** on `POST /sessions/{id}/messages`:
```
event: text_delta     data: {"delta": "..."}
event: tool_start     data: {"tool": "search_reddit", "description": "Searching r/BuyItForLife..."}
event: tool_end       data: {"tool": "search_reddit", "result_summary": "Found 8 posts"}
event: tool_error     data: {"tool": "search_reddit", "error": "Request timed out"}
event: done           data: {"session_id": "...", "title": "..."}
event: error          data: {"message": "Claude API unavailable"}
```

**`first_session_at` behaviour:**
- When any message is saved and `profile.first_session_at IS NULL`: set it to `now()`
- After this write, `GET /health` returns `first_run: false`

**Frontend (React + Vite + TypeScript):**
- Layout: fixed left sidebar (240px) + main chat area
- Sidebar: session list, new chat button, "Information" link, "Settings" link
- Chat area header: mode selector pill tabs (General · Shopping · Diet · Fitness · Lifestyle)
- Messages: user right-aligned, assistant left-aligned, rendered via `react-markdown` + `remark-gfm`
- Tool-use progress strip: `tool_start` events append a status line ("Searching r/BuyItForLife…"); replaced by `tool_end` summary or `tool_error` notice; strip collapses after `done`; expandable on click
- Tool error format: `⚠ {tool} failed — {error}` in amber muted text; non-blocking
- Streaming: token deltas append to in-progress assistant bubble in real time
- Keyboard: Enter sends; Shift+Enter newline; Escape clears input
- Error state: `event: error` shows "Could not reach Claude. Check your API key." — no indefinite spinner
- `session_start_prompt` from `POST /sessions` response: if non-null, rendered as first assistant message in the session before user types
- `make dev`: `npm run dev` + `uvicorn src.weles.api.main:app --reload` via `concurrently`
- `make build`: `npm run build` → FastAPI mounts `frontend/dist/` at `/` via `StaticFiles`; no Node process in production

**Settings page (`/settings`):**
- Accessible from sidebar; sections:
  1. **Notifications** — follow-up cadence (`Off / Weekly / Monthly`); calls `PATCH /settings {follow_up_cadence}`
  2. **Proactive surfacing** — toggle on/off; calls `PATCH /settings {proactive_surfacing}`
  3. **Profile decay thresholds** — editable number inputs per category (days); calls `PATCH /settings {decay_thresholds}`
  4. **Data** — "Clear all data" button; shows confirmation modal ("This will delete all sessions, history, profile, and preferences. Cannot be undone."); calls `DELETE /data`

**Tests shipped with this issue:**
- `tests/integration/test_api.py` (uses `client` fixture from conftest):
  - `POST /sessions` returns 201 with correct shape including `session_start_prompt: null`
  - `GET /sessions` returns empty array on fresh DB
  - `DELETE /sessions/{id}` returns 204; subsequent `GET /sessions/{id}/messages` returns 404
  - `PATCH /sessions/{id}` with `{mode: "shopping"}` updates mode
  - `PATCH /settings` with unknown key returns 422
  - `PATCH /settings` with `{follow_up_cadence: "weekly"}` updates correctly
  - `DELETE /data` returns 204; `GET /sessions` returns empty array after
- `tests/integration/test_sse.py` (uses `mock_claude` + `client`):
  - `POST /sessions/{id}/messages` returns SSE content-type header
  - Stream includes at least one `text_delta` event and a `done` event
  - `done` event carries `title` equal to first 50 chars of the user message

**Technical notes:**
- CORS: `localhost:5173` allowed in dev only; not configured in production (same-origin)
- `react-markdown`: `npm install react-markdown remark-gfm`
- `DELETE /data`: calls `alembic downgrade base` then `alembic upgrade head` to reset schema cleanly
- The CLI `src/weles/__main__.py` is deleted in this issue; `uv run weles` now starts the server
- `src/weles/api/main.py` wires `lifespan = asynccontextmanager` calling `startup()` from #4

**Dependencies:** #4

---

## v0.2 — Personalization

### Issue #6: User profile model and API

**Goal:** Define and persist the user profile using the schema from #3. Provide typed Pydantic models and a clean read/write API.

**Acceptance criteria:**
- `UserProfile` Pydantic model in `src/weles/profile/models.py` mirrors the `profile` table exactly; all fields `Optional` with `None` default
- Enums in same file: `Build`, `FitnessLevel`, `AestheticStyle`, `BudgetPsychology`, `ActivityLevel`, `LivingSituation`, `DietaryApproach` — each a `str` enum matching DB values
- `GET /profile` → full profile; nulls included, not omitted
- `PATCH /profile` → partial update; validates enums; rejects unknown field names with 422
- On write: `field_timestamps[field] = now().isoformat()` for every changed field, in the same DB transaction as the field update
- `src/weles/db/profile_repo.py`: `get_profile() -> UserProfile`, `update_profile(patch: dict) -> UserProfile`
- Helper `profile_is_empty(profile: UserProfile) -> bool` returns True when all non-timestamp fields are None

**Tests shipped with this issue:**
- `tests/unit/test_profile_model.py`:
  - `profile_is_empty(UserProfile())` returns True
  - `profile_is_empty(UserProfile(fitness_level="beginner"))` returns False
  - `UserProfile(build="invalid")` raises `ValidationError`
- `tests/integration/test_profile_api.py` (uses `client`):
  - `PATCH /profile {"fitness_level": "beginner"}` returns 200 with updated field
  - `PATCH /profile {"fitness_level": "invalid"}` returns 422
  - `PATCH /profile {"unknown_field": "x"}` returns 422
  - `field_timestamps` contains `"fitness_level"` key after a write to that field
  - `field_timestamps` does not contain `"weight_kg"` if `weight_kg` was not written

**Technical notes:**
- `field_timestamps` update: read existing JSON, update changed keys, write back atomically
- Enum values stored as plain strings in SQLite; Pydantic coerces on read
- `profile_repo.py` uses a raw `sqlite3` connection from `get_db()`; Pydantic models map rows via `model_validate(dict(row))`

**Dependencies:** #3

---

### Issue #7: Mode selector — UI and system prompt routing

**Goal:** User explicitly picks a domain mode; mode is stored per session and shapes the system prompt for every message in that session.

**Acceptance criteria:**
- Mode stored in `sessions.mode`; updated via `PATCH /sessions/{id} {mode: "shopping"}`; default `general`
- `build_system_prompt(mode: str, profile: UserProfile | None, preferences: list) -> list[dict]` in `src/weles/agent/prompts.py`:
  - Block 1 (always): contents of `system.md`
  - Block 2 (if mode ≠ general): contents of `prompts/modes/{mode}.md`
  - Block 3 (if profile non-empty): profile context block (stub returning `""` until #8 implements it)
  - Returns Anthropic `system` array format: `[{"type": "text", "text": "..."}]`
- Mode addendum content committed in `prompts/modes/`:
  - `shopping.md`: "You are in Shopping mode. Research community consensus on products. Structure responses: consensus → failure modes → red flags → buy timing. Apply the user's budget psychology and aesthetic preferences as hard filters."
  - `diet.md`: "You are in Diet mode. Dietary restrictions are hard constraints — never violate them. Flag evidence strength on supplements explicitly. Surface subreddit culture conflicts."
  - `fitness.md`: "You are in Fitness mode. Prioritise community-vetted programs. Check the user's current program before recommending a switch. Injury history filters out contraindicated movements."
  - `lifestyle.md`: "You are in Lifestyle mode. Prioritise sustained-use reports over trend-driven content. Source age is critical — flag it always."
- Frontend mode selector calls `PATCH /sessions/{id}` on tab change; affects only messages sent after the change

**Tests shipped with this issue:**
- `tests/unit/test_prompts.py`:
  - `build_system_prompt("general", None, [])` returns list of length 1
  - `build_system_prompt("shopping", None, [])` returns list of length 2; second block contains "Shopping mode"
  - `build_system_prompt("shopping", full_profile, [])` returns list of length 3 once #8 is merged (stub: still 2 until then)
  - `build_system_prompt("unknown_mode", None, [])` raises `ValueError`
- `tests/integration/test_mode.py` (uses `client`):
  - `PATCH /sessions/{id} {"mode": "shopping"}` returns 200 with updated mode
  - `PATCH /sessions/{id} {"mode": "invalid"}` returns 422

**Technical notes:**
- `prompts.py` loads mode files via `resource_path(f"src/weles/prompts/modes/{mode}.md")`
- Mode change mid-session is permitted; only messages sent after the change use the new mode prompt

**Dependencies:** #5, #6

---

### Issue #8: Profile context injection

**Goal:** The user's profile and learned preferences are serialised into a compact block and injected as the final system block on every Claude request.

**Acceptance criteria:**
- `build_profile_block(profile: UserProfile, preferences: list[Preference]) -> str | None` in `src/weles/profile/context.py`
- Returns `None` when `profile_is_empty(profile)` is True and `preferences` is empty — no block injected
- Format (null fields omitted entirely):
  ```
  [User Profile]
  Body: 178cm, 80kg, athletic build, intermediate fitness
  Diet: No restrictions. Approach: flexible.
  Style: Minimal aesthetic. Rejects: fast fashion brands.
  Location: PL. Climate: temperate. Living: urban.
  Budget: Buy once, buy right.
  Goals: Build lean muscle. Reduce processed food intake.
  Learned preferences:
  - Does not want minimalist footwear recommendations.
  ```
- `build_system_prompt` in `prompts.py` updated to call `build_profile_block` and append as Block 3 when non-null
- Block regenerated fresh on every request (profile editable mid-session)
- Token estimate logged as warning if over 500 tokens (never truncated — quality over cost)

**Tests shipped with this issue:**
- `tests/unit/test_profile_context.py`:
  - `build_profile_block(UserProfile(), [])` returns `None`
  - `build_profile_block(UserProfile(fitness_level="beginner"), [])` returns string containing "beginner"
  - `build_profile_block(UserProfile(fitness_level="beginner", weight_kg=None), [])` does not contain "weight"
  - `build_profile_block(full_profile, [pref])` contains preference value in output
  - Token estimate of fully populated profile + 5 preferences stays under 500

**Technical notes:**
- `Preference` model: `{id, dimension, value, reason, source}`; loaded from `preferences` table in `profile_repo.py`
- Null arrays (e.g. empty `injury_history`) treated same as null scalar — omitted

**Dependencies:** #6, #7

---

### Issue #9: Information tab

**Goal:** A dedicated UI view showing everything Weles knows about the user — profile fields, learned preferences, history summary. All editable inline. Stale fields flagged. The primary transparency surface.

**Acceptance criteria:**
- Route `/information` in frontend; sidebar link "Information"
- Sections:
  1. **Identity & Body** — height, weight, build, fitness level, injury history
  2. **Diet** — restrictions, preferences, approach
  3. **Style & Taste** — aesthetic style, brand rejections
  4. **Lifestyle** — climate, country, activity level, living situation
  5. **Budget** — budget psychology
  6. **Goals** — fitness goal, dietary goal, lifestyle focus
  7. **Learned Preferences** — all `preferences` rows; each shows value, reason, source badge; delete button calls `DELETE /preferences/{id}`
  8. **History Summary** — count per domain per status ("Shopping: 4 recommended, 2 bought"); link to `/history`
- Each profile field:
  - Shows current value or "Not set" (muted)
  - Shows last updated date from `field_timestamps`
  - Amber dot indicator if past decay threshold (thresholds from `GET /settings`); tooltip: "Last set X days ago"
  - Click → inline edit (text input or dropdown for enums); Enter or blur saves via `PATCH /profile`
- No confirmation modal on preference delete — immediately reversible by re-adding via conversation

**Tests shipped with this issue:**
- No backend tests needed — all new logic is frontend-only; existing `GET /profile` and `DELETE /preferences/{id}` are already covered by other issues

**Technical notes:**
- Decay check in frontend: `Date.now() - Date.parse(field_timestamps[field]) > threshold_days * 86400000`
- History summary: `GET /history` with no filters; group client-side by domain + status

**Dependencies:** #6, #5, #12

---

### Issue #10: Settings page

**Goal:** A dedicated UI page for all app-wide settings — notification cadence, proactive surfacing, decay thresholds, and data management. Backend API already exists from #5.

**Acceptance criteria:**
- Route `/settings` in frontend; sidebar link "Settings"
- **Notifications section:**
  - Follow-up cadence selector: Off / Weekly / Monthly
  - On change: `PATCH /settings {"follow_up_cadence": "weekly"}`
- **Proactive surfacing section:**
  - Toggle switch (on/off)
  - On change: `PATCH /settings {"proactive_surfacing": "true"|"false"}`
- **Profile decay thresholds section:**
  - Five number inputs labelled: Goals (days), Fitness level (days), Dietary approach (days), Body metrics (days), Taste & lifestyle (days)
  - Pre-populated from `GET /settings` → `decay_thresholds` JSON value
  - Save button: `PATCH /settings {"decay_thresholds": {...}}`
- **Data section:**
  - "Clear all data" button
  - Confirmation modal: "This will permanently delete all sessions, history, profile, and preferences. Cannot be undone."
  - On confirm: `DELETE /data`; redirect to `/`
- All fields load from `GET /settings` on mount; show current values

**Tests shipped with this issue:**
- No new backend tests — `GET /settings`, `PATCH /settings`, and `DELETE /data` already covered in #5
- Frontend behaviour is tested manually

**Dependencies:** #5

---

### Issue #11: Proactive information gathering

**Goal:** When the user asks a question in a mode that requires a profile field that is null, the agent asks for it — at most one question per response, never repeated in the same session.

**Acceptance criteria:**
- `check_missing_fields(mode: str, profile: UserProfile) -> list[str]` in `src/weles/agent/context.py`
- Relevant fields per mode:
  - `shopping`: `budget_psychology`, `aesthetic_style`, `country`
  - `diet`: `dietary_restrictions`, `dietary_approach`
  - `fitness`: `fitness_level`, `injury_history`
  - `lifestyle`: `living_situation`, `climate`
  - `general`: always returns `[]`
- Returns only fields that are null in the current profile
- Before each Claude request: if `check_missing_fields` returns non-empty and the field hasn't been asked this session, append to the user turn: `"[System: Profile fields unset and relevant: {fields}. Infer from user message if possible and call save_profile_field. Otherwise ask for at most one.]"`
- Claude tool: `save_profile_field(field: str, value: str)` — calls `update_profile({field: value})`; registered in `ToolRegistry`
- `asked_this_session: set[str]` stored on `Session` object; updated after each ask; persists for session lifetime only

**Tests shipped with this issue:**
- `tests/unit/test_context.py`:
  - `check_missing_fields("shopping", UserProfile())` returns `["budget_psychology", "aesthetic_style", "country"]`
  - `check_missing_fields("shopping", UserProfile(budget_psychology="good_enough"))` returns `["aesthetic_style", "country"]`
  - `check_missing_fields("general", UserProfile())` returns `[]`
  - `check_missing_fields("diet", UserProfile(dietary_restrictions=["gluten"]))` returns `["dietary_approach"]`
- `tests/unit/test_save_profile_field.py`:
  - `save_profile_field("fitness_level", "beginner")` calls `update_profile` with correct args
  - `save_profile_field("unknown_field", "x")` raises `ValueError`

**Dependencies:** #8, #7

---

### Issue #12: Ownership and history tracking

**Goal:** The agent records everything it recommends and everything the user reports owning or having tried, and injects relevant history as context.

**Acceptance criteria:**
- Claude tool: `add_to_history(item_name, category, domain, status, rating=None, notes=None)`
  - `status=recommended` → sets `follow_up_due_at = now() + cadence_days` (null if cadence=off)
  - `status=bought` or `status=tried` → sets `check_in_due_at`: fitness/diet = now()+30d, shopping/lifestyle = now()+90d
  - Registered in `ToolRegistry`
- `GET /history?domain=&status=` returns items most-recent-first; both params optional
- `DELETE /history/{id}` → 204
- History context injection: `get_history_context(domain: str) -> str | None` in `src/weles/db/history_repo.py`
  - Queries `SELECT * FROM history WHERE domain=? ORDER BY created_at DESC LIMIT 10`
  - Returns formatted string: `"[History — Shopping]\nOwned: Red Wing 875 (footwear, bought, rated 5/5).\nTried: Blundstones (footwear, tried, notes: too narrow)."`
  - Returns `None` if no history for that domain
  - Injected into user turn context (not system prompt) when non-null
- `/history` page in frontend: table with columns item, category, domain, status, rating, date; filterable by domain and status; delete button per row

**Tests shipped with this issue:**
- `tests/integration/test_history.py` (uses `client`):
  - `add_to_history(...)` with `status="recommended"` and cadence=weekly sets `follow_up_due_at` to ~7 days from now
  - `add_to_history(...)` with `status="recommended"` and cadence=off leaves `follow_up_due_at` null
  - `add_to_history(...)` with `status="bought"` and `domain="fitness"` sets `check_in_due_at` to ~30 days from now
  - `add_to_history(...)` with `status="bought"` and `domain="shopping"` sets `check_in_due_at` to ~90 days from now
  - `GET /history?domain=shopping` returns only shopping items
  - `GET /history?status=recommended` returns only recommended items
  - `DELETE /history/{id}` removes item; subsequent GET returns 404
- `tests/unit/test_history_context.py`:
  - `get_history_context("shopping")` with no shopping history returns `None`
  - `get_history_context("shopping")` with 2 shopping items returns string containing both item names

**Dependencies:** #8, #5

---

## v0.3 — Research Engine

### Issue #13: Tool-use progress via structured SSE events

**Goal:** Every tool invocation during a research turn emits progress events the frontend can display in real time.

**Acceptance criteria:**
- `stream.py` emits `ToolStartEvent`, `ToolEndEvent`, `ToolErrorEvent` around every `dispatch()` call
- `ToolStartEvent.description` human-readable strings per tool:
  - `search_reddit` → `"Searching r/{', '.join(subreddits)} for '{query}'…"` (or `"Searching Reddit for '{query}'…"` if no subreddits)
  - `search_web` → `"Searching web for '{query}'…"`
  - `add_to_history` → `"Saving {item_name} to history…"`
  - `save_profile_field` → `"Saving {field} to your profile…"`
  - all other tools → `"Running {tool_name}…"`
- `ToolEndEvent.result_summary`: returned by each tool handler as a short string (e.g. `"Found 7 posts (top score: 342)"`)
- `ToolErrorEvent.error`: exception message; tool dispatch catches all exceptions and emits this event rather than propagating
- Claude told on tool error: `"Tool {name} failed: {error}. Continue with available data; note the limitation in your response."`
- Frontend collapsible activity strip: one line per tool call; auto-collapses on `done` event; click to expand

**Tests shipped with this issue:**
- `tests/unit/test_stream_events.py`:
  - `ToolStartEvent(tool="search_reddit", description="…")` serialises to correct SSE `tool_start` JSON
  - `ToolErrorEvent` serialises to correct `tool_error` JSON
  - Dispatching a tool that raises an exception emits `ToolErrorEvent` and does not re-raise

**Technical notes:**
- Tool handlers return a `ToolResult(summary: str, data: Any)` named tuple; `summary` is used for `ToolEndEvent.result_summary`, `data` is serialised and returned to Claude as the tool result
- `ToolErrorEvent` does not abort the SSE stream; dispatch catches, emits, returns an error string to Claude, and continues

**Dependencies:** #5

---

### Issue #14: Reddit search tool

**Goal:** The agent can search Reddit for community discussions using the public JSON API — no credentials required.

**Acceptance criteria:**
- Claude tool: `search_reddit(query, subreddits=None, limit=10, sort="relevance", time_filter="year") -> list[RedditPost]`
- `RedditPost`: `{title, url, score, created_utc, subreddit, selftext_preview (first 500 chars), top_comments: [{body, score}]}`
- When `subreddits` provided: one request per subreddit via subreddit-scoped endpoint; results merged, deduplicated by URL, sorted by score descending
- Top 3 comments fetched via separate request; sorted by score
- Posts with score < 5 excluded before returning
- Rate limiting: `asyncio.Semaphore(1)` shared across all Reddit calls in the process; `asyncio.sleep(1.0)` after each request; backoff on 429: sleep `Retry-After` or 10s; max 3 retries per request
- After 3 consecutive failures on one request: raise `RedditUnavailableError`; `dispatch.py` catches and emits `ToolErrorEvent`; returns empty list to Claude
- `max_tool_calls_per_turn` limit enforced in `dispatch.py`: reads from settings; if current turn has already made N tool calls, any further tool call raises `MaxToolCallsError`, emitted as `ToolErrorEvent`, stream continues to synthesis

**Tests shipped with this issue:**
- `tests/unit/test_reddit.py` (uses `pytest-httpx`):
  - Successful response with 3 posts returns list of 3 `RedditPost` objects with correct fields
  - Post with score=3 excluded from results
  - 429 response triggers retry; succeeds on second attempt
  - 3 consecutive failures raise `RedditUnavailableError`
  - `User-Agent` header present on every request
  - `raw_json=1` parameter present on every request
  - Deduplication: two subreddit searches returning the same post URL produce one result
- `tests/unit/test_tool_limit.py`:
  - Dispatching a 7th tool call when limit=6 raises `MaxToolCallsError`

**Technical notes:**
- Endpoints:
  - All-Reddit: `GET https://www.reddit.com/search.json?q={q}&sort={sort}&t={time_filter}&limit={limit}&raw_json=1`
  - Subreddit-scoped: `GET https://www.reddit.com/r/{sub}/search.json?q={q}&restrict_sr=true&sort={sort}&t={time_filter}&limit={limit}&raw_json=1`
  - Comments: `GET https://www.reddit.com/r/{sub}/comments/{id}.json?limit=5&depth=1&raw_json=1`
- `User-Agent: Weles/0.1` on every request
- `max_tool_calls_per_turn` default is `6` (seeded in `settings` by #3)

**Dependencies:** #13

---

### Issue #15: Subreddit routing by mode and category

**Goal:** The agent selects the most relevant subreddits from config for each research query — no hardcoded lists, no separate classifier call.

**Acceptance criteria:**
- `config/subreddits.toml` populated with full subreddit lists per domain/category:
  ```toml
  [shopping.general]
  subreddits = ["BuyItForLife", "frugalmalefashion", "femalefashionadvice"]
  [shopping.footwear]
  subreddits = ["goodyearwelt", "BuyItForLife", "malefashionadvice"]
  [shopping.electronics]
  subreddits = ["hardware", "headphones", "MechanicalKeyboards"]
  [shopping.kitchen]
  subreddits = ["BuyItForLife", "Cooking", "castiron"]
  [diet.general]
  subreddits = ["nutrition", "EatCheapAndHealthy", "MealPrepSunday"]
  [diet.keto]
  subreddits = ["keto", "ketogains"]
  [diet.vegan]
  subreddits = ["veganfitness", "PlantBasedDiet"]
  [fitness.general]
  subreddits = ["Fitness", "weightroom", "bodyweightfitness"]
  [fitness.running]
  subreddits = ["running", "trailrunning", "BuyItForLife"]
  [fitness.supplements]
  subreddits = ["Supplements", "nattyorjuice", "veganfitness"]
  [lifestyle.general]
  subreddits = ["BuyItForLife", "minimalism", "organization"]
  [lifestyle.coffee]
  subreddits = ["Coffee", "espresso", "BuyItForLife"]
  [lifestyle.home]
  subreddits = ["BuyItForLife", "homeowners", "organization"]
  ```
- `get_subreddits(mode: str, subcategory: str | None) -> list[str]` in `src/weles/research/routing.py`
  - Falls back to `{mode}.general` if subcategory not found
  - Falls back to `["BuyItForLife"]` if mode not found entirely
- Config loaded once at startup via `resource_path`; cached in module-level dict
- Research system prompt instructs Claude to use its reasoning to select the most specific subcategory available when calling `search_reddit`
- User can override: explicit subreddit in user message passed directly to `search_reddit`

**Tests shipped with this issue:**
- `tests/unit/test_routing.py`:
  - `get_subreddits("shopping", "footwear")` returns `["goodyearwelt", "BuyItForLife", "malefashionadvice"]`
  - `get_subreddits("shopping", "nonexistent")` falls back to shopping.general list
  - `get_subreddits("nonexistent_mode", None)` returns `["BuyItForLife"]`
  - `get_subreddits("fitness", "running")` returns running-specific list

**Dependencies:** #14

---

### Issue #16: Web search fallback tool

**Goal:** The agent can search the open web for community-sourced content when Reddit coverage is thin. Absent Tavily key → tool not registered, no crash.

**Acceptance criteria:**
- Claude tool: `search_web(query, limit=8) -> list[WebResult]`; only registered when `app.state.web_search_available` is True
- `WebResult`: `{title, url, snippet, domain, source_type: "community"|"commercial"|"unknown"}`
- `source_type` assignment:
  - domain in `community_domains.txt` → `"community"`
  - domain in `commercial_domains.txt` → `"commercial"`
  - otherwise → `"unknown"`
- Results sorted before return: community first, commercial last
- Tavily request: `POST https://api.tavily.com/search` with `search_depth: "advanced"`, `max_results: limit`, `include_raw_content: false`; Tavily's `answer` field ignored — raw results only
- On any Tavily error: emit `ToolErrorEvent`; return empty list to Claude

**Tests shipped with this issue:**
- `tests/unit/test_web_search.py` (uses `pytest-httpx`):
  - Successful Tavily response parsed into list of `WebResult` objects
  - Domain from `community_domains.txt` gets `source_type="community"`
  - Domain from `commercial_domains.txt` gets `source_type="commercial"`
  - Unknown domain gets `source_type="unknown"`
  - Community results appear before commercial in sorted output
  - Tavily 500 error emits `ToolErrorEvent` and returns empty list
- `tests/unit/test_tool_registration.py`:
  - `get_tool_schemas()` excludes `search_web` when `web_search_available=False`
  - `get_tool_schemas()` includes `search_web` when `web_search_available=True`

**Technical notes:**
- Domain lists loaded at startup via `resource_path`; cached in module-level sets
- Tool registered conditionally in `src/weles/api/startup.py` after `web_search_available` is set

**Dependencies:** #14

---

### Issue #17: Source credibility scoring

**Goal:** Every search result is tagged with a credibility label before Claude sees it, discounting low-signal and potentially biased sources.

**Acceptance criteria:**
- `score_result(result: RedditPost | WebResult) -> CredibilityLabel` in `src/weles/research/credibility.py`
- `CredibilityLabel`: `"high" | "medium" | "low" | "flagged"`
- Reddit rules (applied in order; highest reached label wins):
  - `score 5–19` → `low`
  - `score 20–99` → `medium`
  - `score ≥ 100` → `high`
  - body matches long-term ownership: `r'\b(owned?|had|using|used)\b.{0,40}\b(\d+)\s*(year|month)s?\b'` → promote one tier
  - body matches "switched from": `r'\bswitched?\s+(from|away\s+from)\b'` → promote one tier
- Web rules:
  - `source_type="community"` → `high`
  - `source_type="unknown"` → `medium`
  - `source_type="commercial"` → `low`
  - URL contains affiliate pattern (`?ref=`, `?aff=`, `?tag=`, `/go/`, `/out/`, `/recommends/`) → `flagged` (regardless of other label)
- Batch check: if ≥ 3 results in same call are `low` or `flagged` and share ≥ 4 word n-gram overlap → set `batch_flag="coordinated_positivity"` on the result set
- `credibility` field appended to each result; `batch_flag` appended as top-level field on result set
- Research prompt instructs Claude: "Heavily discount `low` and `flagged` results. If `coordinated_positivity` is set, mention possible astroturfing."

**Tests shipped with this issue:**
- `tests/unit/test_credibility.py`:
  - Reddit post score=50 → `medium`
  - Reddit post score=150 → `high`
  - Reddit post score=50 + ownership pattern in body → `high` (promoted)
  - Web result with community domain → `high`
  - Web result URL containing `?ref=` → `flagged`
  - 3 low-credibility results with shared 4-gram → `batch_flag="coordinated_positivity"`
  - 2 low-credibility results with shared 4-gram → no batch flag (below threshold)
  - Score promotion capped at `high` (can't promote past it)

**Technical notes:**
- N-gram overlap: `ngrams(text, 4) = {tuple(words[i:i+4]) for i in range(len(words)-3)}` where `words = text.lower().split()`
- All functions pure and synchronous; no external deps

**Dependencies:** #14, #16

---

### Issue #18: Research synthesis, error resilience, and tool call cap

**Goal:** Claude synthesises community research into structured, calibrated responses. Tool failures surface as notices but never abort synthesis. A hard cap prevents runaway tool loops.

**Acceptance criteria:**
- `src/weles/prompts/research.md` committed; injected into user turn as a system note when the first research tool call is made:
  ```
  [Research guidance]
  - Open with signal strength: [strong consensus] / [divided community] / [thin data]
  - Surface dissenting views when a vocal minority exists
  - Flag data older than 3 years: "Note: most discussion on this dates to [year]."
  - Flag discontinued products explicitly
  - Never use manufacturer language, spec-sheet comparisons, or affiliate superlatives
  - Show reasoning: not "buy X" but "Long-term owners prefer X because Y. Common failure point: Z."
  - When communities disagree, present both sides labelled by source — do not pick a side unless the user's profile provides clear directional preference
  ```
- Tool failure handling: each `ToolErrorEvent` adds to a `failed_tools` list on the stream; after all tools complete, if `failed_tools` non-empty, Claude receives: `"The following tools failed: {failed_tools}. Continue with available data. State in your response which sources were unavailable."`
- Claude always produces a response — never just an error message
- `[thin data]` used when: fewer than 3 relevant posts found across all searches, or all searches failed
- `max_tool_calls_per_turn` enforced: `dispatch.py` tracks call count per stream; on exceeding limit emits `ToolErrorEvent("max_tool_calls", "Research limit reached")` and refuses further calls; Claude told: "Research limit reached. Synthesise with what you have."
- `scripts/eval_research.py`: runs 5 representative queries against live Claude; prints results for manual review (not a CI test — requires API key)

**Tests shipped with this issue:**
- `tests/unit/test_synthesis.py`:
  - `failed_tools=["search_reddit"]` produces correct failure message string
  - `failed_tools=[]` produces no failure message
- `tests/unit/test_tool_limit.py` (extends from #14):
  - Tool call count resets between sessions
  - Exceeding limit emits correct `ToolErrorEvent` and returns sentinel string to Claude

**Technical notes:**
- Research prompt not injected for General mode queries that don't trigger any tool call — it activates only when `tool_start` is first emitted in a turn
- `max_tool_calls_per_turn` read from `settings` table at stream start; default 6

**Dependencies:** #17

---

## v0.4 — Domain Modules

### Issue #19: Shopping mode

**Goal:** Full end-to-end implementation of Shopping mode: intent handling, tool-use sequence, profile filters, and structured response format.

**Acceptance criteria:**

**Sub-intents (Claude classifies from message, no separate call):**
- `category_research` — "best waterproof jacket under $200"
- `product_lookup` — "what do people think of Red Wing 875"
- `comparative` — "Danner vs Red Wing for everyday wear"
- `buy_timing` — "good time to buy a road bike"

**Tool-use sequence for `category_research`:**
1. Claude selects 3–5 subreddits via `get_subreddits("shopping", subcategory)`
2. Calls `search_reddit(query="best {category} {budget}", subreddits=[...], time_filter="year")`
3. If results < 3 relevant posts: calls `search_web("{category} recommendations site:reddit.com")`
4. Credibility scoring applied by tool handlers; labels present in returned data
5. Claude synthesises with research prompt active
6. Calls `add_to_history` for each specifically recommended product with `status="recommended"`
7. If `budget_psychology` or `aesthetic_style` null: proactive gather triggers (per #11)

**Response structures:**

`category_research`:
```
[signal strength]
Community pick: {item} — {reason from owner reports}
Long-term owners report: {durability/longevity}
Common failure point: {issue}
Red flags: {QC regressions, quality decline — if any}
Buy timing: {community-reported sale patterns — if available}
```

`product_lookup`:
```
[signal strength]
Community consensus: {summary}
Reported strengths: {from owner threads}
Reported weaknesses / failure modes: {recurring complaints}
What people switched to (and why): {if data exists}
```

`comparative`:
- Never a spec-sheet diff
- Framed as community-origin perspectives: "r/X users lean toward A because… r/Y users prefer B because…"
- Explicit note when subreddits contradict each other

**Profile filters:**
- `budget_psychology=buy_once_buy_right` → bias toward longevity posts; surface price-per-use framing
- `budget_psychology=good_enough` → surface value picks; note trade-off
- `aesthetic_style` → instruct Claude to deprioritise results conflicting with stated style
- `country` → note limited regional availability when detectable

**Tests shipped with this issue:**
- `tests/integration/test_shopping_mode.py` (uses `mock_claude` + `client`):
  - Session in shopping mode: mock Claude returns a `search_reddit` tool call; verify `search_reddit` is dispatched and result returned to Claude
  - `add_to_history` tool call from Claude is dispatched and persisted in DB
  - History context injected in user turn for shopping domain when history exists

**Dependencies:** #18, #12, #15

---

### Issue #20: Diet mode

**Goal:** Full implementation of Diet mode: meal suggestions, approach validation, and supplement guidance — hard-constrained by dietary restrictions.

**Acceptance criteria:**

**Sub-intents:**
- `meal_suggestion` — "high protein breakfast ideas"
- `approach_validation` — "should I try keto"
- `supplement_guidance` — "is creatine worth it"
- `recipe_sourcing` — "community recipes for high-protein pasta"

**Dietary restrictions enforcement:**
- `dietary_restrictions` from profile injected into diet mode system prompt as: `"Hard constraints: user cannot eat {restrictions}. Never suggest items containing these. Discard research results that include them."`
- This constraint is present whether or not the research prompt is active

**Tool-use sequence for `approach_validation`:**
1. Search approach-specific subreddit first (inside view)
2. Search `r/nutrition` second (outside view)
3. If communities disagree: present both with source labels; do not resolve unless `profile.dietary_approach` is set

**Supplement guidance response structure:**
```
[signal strength]
Community experience: {what people report}
Evidence strength: anecdotal | weak evidence | stronger evidence
(Community-reported experience only — not clinical data.)
Common positive reports: {pattern}
Common negative reports: {pattern}
What people switched to: {if data exists}
```

**`meal_suggestion` sequence:**
1. Build query from `dietary_approach`, `dietary_restrictions`, `dietary_preferences`
2. Search `r/MealPrepSunday`, `r/EatCheapAndHealthy`, approach-specific sub if set
3. Link to original community thread where possible
4. If macros requested and `weight_kg` + `fitness_goal` in profile: show calculation

**Proactive fields checked:** `dietary_restrictions` (always, before any diet query); `dietary_approach` (for approach_validation only)

**Tests shipped with this issue:**
- `tests/unit/test_diet_mode.py`:
  - Diet mode system prompt with `dietary_restrictions=["gluten"]` contains "gluten" in hard constraints block
  - Diet mode system prompt with empty restrictions has no constraints block

**Dependencies:** #18, #12, #15

---

### Issue #21: Fitness mode

**Goal:** Full implementation of Fitness mode: program recommendations anchored to community-vetted programs, check-ins, and troubleshooting with community-first escalation.

**Acceptance criteria:**

**Sub-intents:**
- `program_recommendation` — "what program for hypertrophy"
- `program_check_in` — "I'm 6 weeks into 5/3/1"
- `troubleshoot` — "my squat isn't improving", "shin splints"
- `gear_advice` — routes through fitness subreddits

**`config/programs.toml`** populated:
```toml
[[programs]]
name = "5/3/1"; level = "intermediate"; goal = "strength"; equipment = "barbell"
source = "https://www.reddit.com/r/weightroom/wiki/531"
[[programs]]
name = "GZCLP"; level = "beginner"; goal = "strength"; equipment = "barbell"
source = "https://www.reddit.com/r/Fitness/wiki/gzclp"
[[programs]]
name = "Starting Strength"; level = "beginner"; goal = "strength"; equipment = "barbell"
[[programs]]
name = "PHUL"; level = "intermediate"; goal = "hypertrophy"; equipment = "barbell"
[[programs]]
name = "C25K"; level = "beginner"; goal = "running"; equipment = "none"
source = "https://www.reddit.com/r/C25K/wiki/index"
[[programs]]
name = "Bodyweight Fitness RR"; level = "beginner"; goal = "general"; equipment = "none"
source = "https://www.reddit.com/r/bodyweightfitness/wiki/kb/recommended_routine"
```

**`program_recommendation` sequence:**
1. Check history for `domain=fitness, status IN (bought, tried)` — note current program
2. If current program found: ask "Continue with {program} or switch?" before searching
3. Filter `programs.toml` by `fitness_level`, `fitness_goal`, equipment if known
4. `search_reddit("experiences with {program}")` for top candidates
5. Recommend from filtered list first; go outside list only if no match
6. Include source link for every recommended program
7. Call `add_to_history(status="recommended")` for the suggestion

**Troubleshoot sequence:**
1. `search_reddit("{issue} site:reddit.com OR r/Fitness")` first
2. Community-sourced steps; "see a professional" only for: sharp/acute pain, numbness, recurring injury that isn't resolving

**Injury filter:** if `injury_history` set, fitness mode prompt contains: "Flag if any recommended program includes movements that may conflict with: {injury_history}."

**Proactive fields:** `fitness_level` (any fitness query); `injury_history` (program_recommendation + troubleshoot)

**Tests shipped with this issue:**
- `tests/unit/test_fitness_mode.py`:
  - `programs.toml` loaded correctly; `filter_programs("beginner", "strength", "barbell")` returns GZCLP and Starting Strength
  - Injury history present in system prompt when profile has `injury_history`

**Dependencies:** #18, #12, #15

---

### Issue #22: Lifestyle mode

**Goal:** Full implementation of Lifestyle mode: product ecosystem, maintenance, and organisation — biased toward sustained-use reports, source age always flagged.

**Acceptance criteria:**

**Sub-intents:**
- `product_ecosystem` — "what pairs well with my Aeropress"
- `maintenance_care` — "how do I care for raw denim"
- `organisation` — "cable management solutions people actually use"
- `routine` — "morning routine products people stick with"

**`product_ecosystem` sequence:**
1. Extract owned item(s) from message; cross-reference with history
2. `search_reddit("{item} accessories OR pairs well long term")` via BuyItForLife + relevant community
3. `search_web("{item} pairs with site:{forum}")` for known hobbyist forums in `community_domains.txt`
4. Results > 3 years old flagged in synthesis

**Anti-trend enforcement (from `lifestyle.md`):**
- "Prioritise posts reporting sustained use of 1+ year."
- Source age always surfaced: "Most discussion on this is from [year]."

**Maintenance guidance:**
- Community-sourced steps only; manufacturer instructions used only as secondary confirmation
- Failure cases included: "Users who used X on Y material reported Z damage"

**Profile fields used:** `living_situation`, `climate` (applied when relevant); ownership history cross-referenced

**Tests shipped with this issue:**
- No new unit tests required beyond what #18–21 already establish for the mode pattern

**Dependencies:** #18, #12, #15

---

## v0.5 — Learning Loop

### Issue #23: Context window management via message compression

**Goal:** Conversations grow indefinitely without degrading quality. Raw tool results — the largest token source — are replaced with summaries after use. Full message content preserved via summarisation, never dropped.

**Acceptance criteria:**
- `Session.get_messages_for_context() -> list[dict]`: returns all messages with `is_compressed=True` replaced by their summary content
- After each turn where tool results were used, `compress_tool_results(session_id, turn_messages)` runs:
  - For each tool_result message in the turn: call Claude with `"Summarise what this tool result contributed to the response in 2 sentences."` (separate API call, not part of the main stream)
  - Update `messages.content` with `"[Compressed] {summary}"` and set `is_compressed=True` in DB
- If `estimated_tokens(session) > 0.8 * CONTEXT_WINDOW`:
  - Take oldest 25% of user+assistant message pairs (never the last 10 messages)
  - For each pair: call Claude with `"Summarise this exchange in 2-3 sentences, preserving recommendations, decisions, and profile information revealed."`
  - Replace both messages in DB with one summary message; mark originals `is_compressed=True`
- `estimated_tokens(messages) -> int`: `int(len(" ".join(m["content"] for m in messages).split()) * 1.3)`
- `CONTEXT_WINDOW`: read from a constant in `src/weles/agent/session.py`; default 200000

**Tests shipped with this issue:**
- `tests/unit/test_session.py`:
  - `estimated_tokens([])` returns 0
  - `get_messages_for_context()` substitutes compressed content for `is_compressed=True` messages
  - Last 10 messages are never in the compression candidate set
  - Compression threshold: session at 79% of window → no compression; at 81% → triggers

**Technical notes:**
- Compression API calls are fire-and-forget; they do not block the main response stream
- `is_compressed=True` + summary stored in DB; original content is gone — acceptable, the synthesis is the artefact
- `claude-sonnet-4-6` context window: 200k tokens; compression rarely triggers in normal use; the mechanism is there for power users

**Dependencies:** #5, #3

---

### Issue #24: Session start orchestrator

**Goal:** A single function that runs all session-start checks in a defined order, returns at most one user-facing prompt, and prevents conflicts between checks.

**Acceptance criteria:**
- `run_session_start_checks(db: Connection) -> SessionStartResult` in `src/weles/api/session_start.py`
- `SessionStartResult`: `{prompt: SessionStartPrompt | None, notices: list[str]}`
  - `prompt`: one of `follow_up | check_in | decay` — at most one
  - `notices`: zero or more QC alerts / seasonal notices (separate from prompt; shown as system notices above chat)
- Execution order (strict):
  1. **Passive pattern detection** (from #27): runs `SELECT category, COUNT(*) FROM history WHERE status='skipped' GROUP BY domain, category HAVING COUNT(*) >= 3`; for each result, writes a preference via `update_preference(source="agent_inferred")` — no user prompt
  2. **Profile decay check** (from #28): if stale field found → set `prompt = {type: "decay", message: "Your {field} was last set {X} days ago as '{value}'. Still accurate?"}`
  3. **Follow-up check** (from #25): if follow-up due AND no decay prompt → set `prompt = {type: "follow_up", message: "Did you end up getting {item}?"}`
  4. **Check-in check** (from #26): if check-in due AND no prompt yet → set `prompt = {type: "check_in", message: "It's been {N} days since you {bought/started} {item}. How's it going?"}`
  5. **QC / proactive surfacing** (from #31): searches run; high-score alerts added to `notices`
- `POST /sessions` updated to call `run_session_start_checks` and return result in `session_start_prompt` field
- Frontend: if `session_start_prompt.prompt` non-null, render as initial assistant message; if `session_start_prompt.notices` non-empty, render as dismissable system notices above the first message

**Tests shipped with this issue:**
- `tests/unit/test_session_start.py`:
  - With no due items: returns `{prompt: None, notices: []}`
  - With decay due + follow-up due: returns decay prompt (decay wins)
  - With follow-up due + check-in due: returns follow-up prompt (follow-up wins)
  - With check-in due only: returns check-in prompt
  - Passive pattern detection writes preference when ≥ 3 skipped items in same category
  - Passive pattern detection does not return a user-facing prompt

**Technical notes:**
- Steps 1–5 run sequentially; step 5 (QC) runs regardless of whether a prompt was found — notices are independent
- QC checks (step 5) are rate-limited by the 24h cache; won't slow down every session start
- This function is the only place these checks run; individual issues (#25–#28, #31) define *what* each check does, not *when* it runs

**Dependencies:** #12, #6

---

### Issue #25: Post-recommendation follow-up

**Goal:** When follow-up cadence is enabled, the orchestrator surfaces one overdue follow-up per session — never a queue.

**Acceptance criteria:**
- `check_follow_up(db) -> SessionStartPrompt | None` in `src/weles/api/session_start.py`
- Queries: `SELECT * FROM history WHERE status='recommended' AND follow_up_due_at <= now() ORDER BY follow_up_due_at ASC LIMIT 1`
- Returns prompt if result found; `None` otherwise
- User response handling (via Claude tool calls during the session):
  - "Yes, bought it" → `add_to_history` updates `status="bought"`; optionally prompts for rating
  - "Not yet / no" → `UPDATE history SET follow_up_due_at = now() + cadence_days`
  - "Stop asking" → `UPDATE history SET status='skipped'`
- Maximum 1 follow-up prompt per session (enforced by orchestrator in #24)
- Cadence configured in settings (`follow_up_cadence`: off / weekly / monthly); default off

**Tests shipped with this issue:**
- `tests/unit/test_follow_up.py`:
  - `check_follow_up` with no due items returns `None`
  - `check_follow_up` with a due item returns correct prompt message
  - `follow_up_due_at` null when cadence=off (already tested in #12)
  - `follow_up_due_at` set to 7 days from now when cadence=weekly

**Dependencies:** #24

---

### Issue #26: Outcome check-ins

**Goal:** Items the user bought or tried trigger a check-in prompt after enough time has passed.

**Acceptance criteria:**
- `check_check_in(db) -> SessionStartPrompt | None` in `src/weles/api/session_start.py`
- Queries: `SELECT * FROM history WHERE status IN ('bought','tried') AND check_in_due_at <= now() ORDER BY check_in_due_at ASC LIMIT 1`
- Returns prompt if found; `None` otherwise
- Prompt: `"It's been {N} days since you {bought/started} {item_name}. How's it going?"`
- N calculated as `(now() - created_at).days`
- User response handling:
  - Positive → rating stored; notes updated via Claude tool calls
  - Negative / abandoned → notes stored; Claude may call `update_preference` if pattern evident
  - "Remind me later" → `check_in_due_at = now() + 30 days`
- Check-in only surfaces if no follow-up is already due (orchestrator order in #24 enforces this)

**Tests shipped with this issue:**
- `tests/unit/test_check_in.py`:
  - `check_check_in` with no due items returns `None`
  - `check_check_in` with due item returns prompt containing item name
  - Check-in due date for fitness domain item set to ~30 days (tested in #12)
  - Check-in due date for shopping domain item set to ~90 days (tested in #12)

**Dependencies:** #24

---

### Issue #27: Correction memory and passive pattern detection

**Goal:** Explicit pushback immediately updates the preference model. Consistently ignored recommendation types are detected and suppressed automatically by the session start orchestrator.

**Acceptance criteria:**
- Claude tool: `update_preference(dimension, value, reason=None)` in `src/weles/tools/profile_tools.py`
  - `source` set by caller: `"user_explicit"` when triggered by pushback, `"agent_inferred"` when called by passive detection
  - Writes to `preferences` table; does not modify `profile` table
- Preference immediately injected into profile context block (rebuilt on next request)
- Passive pattern detection query (run by orchestrator step 1 in #24):
  ```sql
  SELECT domain, category, COUNT(*) as cnt
  FROM history WHERE status='skipped'
  GROUP BY domain, category HAVING cnt >= 3
  ```
  For each result: `update_preference(dimension=f"{domain}.{category}", value=f"Consistently skips {category} recommendations in {domain}", source="agent_inferred")`
- System prompt contains: "If the user pushes back on a recommendation type or says they're not interested in a category, call `update_preference` immediately."
- `DELETE /preferences/{id}` removes preference; Claude reverts to prior behaviour
- Preferences visible and deletable in Information tab (#9)

**Tests shipped with this issue:**
- `tests/unit/test_preferences.py`:
  - `update_preference("shopping.footwear", "No minimalist", source="user_explicit")` writes correct row
  - Preference row appears in `build_profile_block` output after write
  - Passive detection query with 3 skipped footwear items writes one preference
  - Passive detection query with 2 skipped items writes nothing
- `tests/integration/test_preferences_api.py`:
  - `DELETE /preferences/{id}` removes row; `GET /profile` no longer contains that preference value

**Dependencies:** #24, #8

---

### Issue #28: Profile decay and reconfirmation

**Goal:** Profile fields past their decay threshold surface for reconfirmation once per session — surfaced by the orchestrator, never mid-conversation.

**Acceptance criteria:**
- `check_decay(profile: UserProfile, thresholds: dict) -> SessionStartPrompt | None` in `src/weles/profile/decay.py`
- Decay thresholds from `settings.decay_thresholds`:
  - `goals` → `fitness_goal`, `dietary_goal`, `lifestyle_focus`: 60 days
  - `fitness_level` → `fitness_level`: 90 days
  - `dietary_approach` → `dietary_approach`: 90 days
  - `body_metrics` → `height_cm`, `weight_kg`, `build`: 180 days
  - `taste_lifestyle` → `aesthetic_style`, `climate`, `activity_level`, `living_situation`: 365 days
- Only non-null fields checked (null fields handled by proactive gathering in #11)
- Returns the most overdue field's prompt; `None` if nothing stale
- Prompt: `"Your {field_label} was last set {X} days ago as '{value}'. Still accurate?"`
- User confirms → `field_timestamps[field] = now()`; no value change
- User updates → `update_profile({field: new_value})`
- User ignores → `field_timestamps[field] = now()` (silence = confirmed)
- Information tab shows amber dot for stale fields regardless of whether the session prompt was shown

**Tests shipped with this issue:**
- `tests/unit/test_decay.py`:
  - `check_decay` with all fields updated recently returns `None`
  - `check_decay` with `fitness_goal` updated 61 days ago returns decay prompt for `fitness_goal`
  - Null field not returned as stale (null handled by proactive gathering)
  - Most overdue field selected when multiple are stale
  - Thresholds read from settings dict; configurable

**Dependencies:** #24, #6

---

## v0.6 — Signal Quality

### Issue #29: Explicit confidence calibration

**Goal:** Every research-backed response opens with a signal strength label and shows reasoning. Thin and old data handled honestly.

**Acceptance criteria:**
- `research.md` updated to explicitly require:
  - Open with exactly one of: `[strong consensus]` / `[divided community]` / `[thin data]`
  - `[strong consensus]`: recurring agreement across ≥ 3 high-credibility posts from ≥ 2 subreddits
  - `[divided community]`: meaningful disagreement between credible sources; both sides surfaced with source labels
  - `[thin data]`: < 3 relevant posts found, or all searches failed, or only low-credibility results
  - Minority opinion explicitly named: "A minority of r/X users report…"
  - Data age flagged when all top results > 3 years old: "Note: most community discussion on this dates to [year]."
  - Discontinued products flagged: "Note: [product] appears discontinued."
  - `[thin data]` format: "Community discussion on {topic} is sparse. Available signals: {summary}. Treat as a starting point, not consensus."
- `scripts/eval_confidence.py`: runs 5 queries (obscure product, popular product, divided topic, old product, thin category); prints results for manual review; not a CI gate

**Tests shipped with this issue:**
- `tests/unit/test_research_prompt.py`:
  - `research.md` file exists and contains the string `[strong consensus]`
  - `research.md` contains `[divided community]`
  - `research.md` contains `[thin data]`

**Technical notes:**
- Confidence label is a required output format enforced by prompt, not code
- `eval_confidence.py` requires `ANTHROPIC_API_KEY` in env; usage: `uv run python scripts/eval_confidence.py`

**Dependencies:** #18

---

### Issue #30: Anti-bias and astroturfing heuristics

**Goal:** Affiliate-linked, commercially biased, and potentially astroturfed sources are discounted and labelled before reaching synthesis. Geographic relevance filter applied when country is set.

**Acceptance criteria:**
- Affiliate URL detection extended in `credibility.py` (builds on #17):
  - URLs containing `?ref=`, `?aff=`, `?tag=`, `/go/`, `/out/`, `/recommends/` → `credibility: "flagged"`, attach `affiliate: True`
- Geographic relevance filter:
  - `config/geo_blocks/{country_code}.txt` (e.g. `PL.txt`): newline-separated domain list of retailers not serving that country
  - If `profile.country` is set and result domain is in the country's geo_block file: tag `available: False`
  - Claude instructed: "Exclude `available: False` results from synthesis."
  - If no geo_block file for user's country: skip filter silently
- Coordinated positivity extended (builds on #17): now also checks for uniform 5-star framing phrases (e.g. "exceeded my expectations", "highly recommend") across low-credibility results
- All credibility metadata present in result objects passed to Claude
- Research synthesis prompt updated: "Discount `flagged` and `low` results. If `coordinated_positivity` batch flag is set, note possible astroturfing."

**Tests shipped with this issue:**
- `tests/unit/test_anti_bias.py`:
  - `?ref=` in URL → `flagged` + `affiliate: True`
  - `/go/` in URL → `flagged`
  - Unknown URL with no affiliate params → unaffected
  - Domain in `PL.txt` + `profile.country="PL"` → `available: False`
  - No `PL.txt` file → no `available` tag applied
  - 3 low-credibility results with "exceeded my expectations" in all bodies → `coordinated_positivity`

**Dependencies:** #17

---

### Issue #31: Scoped proactive surfacing

**Goal:** QC alerts and seasonal notices surfaced at session start — only for domains the user has history in, never cold. Run by the session start orchestrator.

**Acceptance criteria:**
- `run_proactive_checks(db, profile) -> list[str]` in `src/weles/api/session_start.py`; called as step 5 of orchestrator (#24)
- **QC monitoring:**
  - For each of the 5 most recent `status IN (bought, tried)` history items:
    - Check 24h cache in `settings` (`key="qc_cache_{item_id}"`); skip if cached result is < 24h old
    - Call `search_reddit("{item_name} quality issue OR defect OR recall", time_filter="month", limit=5)`
    - If any result has score > 50: add notice `"Recent community discussion about quality issues with {item_name}: {url}"`
    - Cache result (found or not) with current timestamp
  - Returns list of notice strings
- **Seasonal surfacing:**
  - Load `config/seasonal.toml`; find entries where current month falls in `months` array
  - For each matching entry: check if user has any history in that `domain`
  - If yes: add notice from `prompt` field
- `proactive_surfacing` setting: if `"false"`, `run_proactive_checks` returns `[]` immediately
- Notices returned in `SessionStartResult.notices`; rendered as dismissable banners above chat

**Tests shipped with this issue:**
- `tests/unit/test_proactive.py`:
  - `run_proactive_checks` with `proactive_surfacing="false"` returns empty list immediately
  - QC cache hit (< 24h old): `search_reddit` not called
  - QC cache miss: `search_reddit` called (mock verifies call)
  - Seasonal entry for current month + user has domain history → notice returned
  - Seasonal entry for current month + user has no domain history → no notice
  - Cap: only first 5 history items checked (not all)

**Technical notes:**
- QC search uses `search_reddit` from #14 (real function call)
- 24h cache prevents QC checks from running on every session start

**Dependencies:** #24, #14

---

## v1.0 — Distribution

### Issue #32: System tray app, PyInstaller packaging, and Windows auto-start

**Goal:** Weles runs as a native Windows app. Starts with the OS, lives in the system tray, opens the browser on click. Single `.exe`. No terminal, no Docker.

**Acceptance criteria:**
- `src/weles/tray.py`:
  - `multiprocessing.freeze_support()` called at very top of file, before any imports
  - FastAPI server started in `threading.Thread(daemon=True, target=lambda: uvicorn.Server(config).run())`
  - System tray icon loaded from `resource_path("assets/icon.ico")` via `pystray`
  - Left-click: opens `http://localhost:{WELES_PORT}` in default browser
  - Right-click menu: Open · Restart server · Quit
  - On first launch (`is_first_run=True` from `GET /health`): browser opens automatically without click
  - Port conflict at startup: tooltip shows "Port {port} already in use"; right-click menu adds "Change port" (writes `WELES_PORT` to `~/.weles/.env`)
  - Quit: sets `server.should_exit = True`; waits up to 5s for thread to finish; calls `sys.exit(0)`
- `weles.spec` PyInstaller spec committed:
  ```python
  a = Analysis(['src/weles/tray.py'],
      datas=[
          ('frontend/dist', 'frontend/dist'),
          ('config', 'config'),
          ('src/weles/prompts', 'src/weles/prompts'),
          ('blocklist', 'blocklist'),
          ('assets', 'assets'),
      ])
  exe = EXE(..., name='Weles', console=False, onefile=True, icon='assets/icon.ico')
  ```
- `make package`: runs `npm run build` then `pyinstaller weles.spec` → `dist/Weles.exe`
- `make install`:
  - Copies `dist/Weles.exe` to `%LOCALAPPDATA%\Weles\Weles.exe`
  - Creates `.lnk` shortcut in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
  - No admin rights required
- `make uninstall`: removes startup shortcut; does not touch `~/.weles/` (data preserved)
- `assets/icon.ico`: real icon file, 16×16 + 32×32 embedded; replaces placeholder from #1
- GitHub Actions `build-windows` job: triggers on `tags: v*.*.*`; runs `make package`; uploads `dist/Weles.exe` as release asset

**Tests shipped with this issue:**
- Manual testing only — PyInstaller output cannot be unit tested meaningfully
- Checklist in PR description:
  - [ ] `Weles.exe` launches without terminal window
  - [ ] Tray icon appears in Windows system tray
  - [ ] Left-click opens browser at correct URL
  - [ ] First launch opens browser automatically
  - [ ] Quit from tray closes server cleanly
  - [ ] Startup shortcut present after `make install`
  - [ ] App starts on Windows login after install
  - [ ] `~/.weles/` data intact after uninstall + reinstall

**Technical notes:**
- `pystray` + `pillow` are runtime deps (add to `pyproject.toml` in this issue)
- Windows Defender may flag unsigned PyInstaller `.exe` — expected for personal tools; note in README
- Code signing is out of scope
- `.env` at `~/.weles/.env` is never bundled — API keys stay on disk
- `uv run weles` in production starts `tray.py`; `make dev` still starts the server directly for development

**Dependencies:** #5, #31
