# Weles — Claude Code Guide

## What this project is

A locally-hosted personal AI agent (FastAPI + React) that advises on shopping, lifestyle, diet, and fitness. All advice is grounded in community sources (Reddit, enthusiast forums) — never manufacturer copy. It builds a persistent profile of the user and applies it to every response. See `plan.md` for the full product vision and `issues.md` for the implementation plan.

---

## Stack

| Layer | Choice |
|---|---|
| LLM | Claude API (`claude-sonnet-4-6`), raw Anthropic SDK, tool_use pattern |
| Backend | FastAPI + SSE streaming, lifespan context manager |
| Frontend | React + Vite + TypeScript, `react-markdown` + `remark-gfm`, EventSource API |
| Storage | SQLite at `~/.weles/weles.db`, WAL mode, Alembic migrations |
| Reddit | `httpx` → public JSON API, no credentials, `raw_json=1` |
| Web search | Tavily API; gracefully absent when key not set |
| Packaging | `pystray` system tray + PyInstaller `.exe` + Windows startup folder |
| Deps | `uv` |

---

## Architectural decisions (A1–A16)

These are binding. Do not re-litigate them.

- **A3** No LangChain or agent framework — raw Anthropic SDK only. Tool surface is small and custom.
- **A5** Reddit via `httpx` to public `.json` endpoints — no app registration, no PRAW.
- **A7** Full schema in one initial Alembic migration (`001_initial.py`). No columns added mid-project.
- **A8** SSE with typed event names: `text_delta`, `tool_start`, `tool_end`, `tool_error`, `done`, `error`.
- **A9** Mode selection is explicit (pill tabs in UI): `general | shopping | diet | fitness | lifestyle`.
- **A10** No structured onboarding — agent asks for missing fields mid-conversation.
- **A11** Context quality over cost. Compress tool results after synthesis; summarise oldest turns at 80% window capacity; never drop messages.
- **A12** Tool failures → inline `ToolErrorEvent` notice; Claude continues. Only hard failure: Claude API down.
- **A14** Distribution: PyInstaller `.exe`, `pystray` tray, Windows startup folder. No Docker, no terminal.
- **A15** Session title = first 50 chars of first user message. No API call.
- **A16** Test mocks: `pytest-mock` for Anthropic SDK; `pytest-httpx` for Reddit and Tavily.

---

## Directory structure

```
weles/
├── src/weles/
│   ├── agent/        # client.py, stream.py, dispatch.py, session.py, prompts.py, context.py
│   ├── api/          # main.py, routers/, startup.py, session_start.py
│   ├── db/           # connection.py, profile_repo.py, history_repo.py, settings_repo.py
│   ├── profile/      # models.py, context.py, decay.py
│   ├── tools/        # reddit.py, web.py, history_tools.py, profile_tools.py
│   ├── research/     # credibility.py, routing.py
│   └── utils/        # paths.py, errors.py
├── frontend/         # React + Vite + TypeScript
├── config/
│   ├── subreddits.toml
│   ├── programs.toml
│   ├── seasonal.toml
│   └── geo_blocks/   # per-country domain blocklists (e.g. PL.txt)
├── blocklist/
│   ├── commercial_domains.txt
│   └── community_domains.txt
├── src/weles/prompts/
│   ├── system.md
│   ├── research.md
│   └── modes/        # shopping.md, diet.md, fitness.md, lifestyle.md
├── alembic/
├── tests/
│   ├── conftest.py   # mock_claude, tmp_db, client fixtures
│   ├── unit/
│   └── integration/
└── scripts/
```

---

## Critical rules — apply everywhere

**`resource_path` is mandatory for all file reads.**
```python
from src.weles.utils.paths import resource_path
path = resource_path("config/subreddits.toml")  # correct
path = Path("config/subreddits.toml")            # WRONG — breaks in PyInstaller
```
`resource_path` returns `Path(sys._MEIPASS) / relative` when frozen, else repo root. Every config, prompt, and blocklist read uses it.

**`first_session_at` is the first-run flag.**
Set it when the user sends their very first message (`profile.first_session_at IS NULL` before write). Never use `onboarding_completed_at` — that column doesn't exist.

**Session start prompts go through the orchestrator.**
`run_session_start_checks()` in `session_start.py` is the only place follow-up, check-in, and decay prompts are triggered. Never call these checks from anywhere else. At most one user-facing prompt per session.

**Tool errors never abort the stream.**
`dispatch.py` catches all tool exceptions, emits `ToolErrorEvent`, returns an error string to Claude, and continues. Only `ConfigurationError` (missing API key) is a hard stop.

**`max_tool_calls_per_turn` is enforced in `dispatch.py`.**
Read from `settings` at stream start. Default: 6. Exceeding it emits `ToolErrorEvent("max_tool_calls", "Research limit reached")`.

**No dropped messages.**
Context compression (Issue #23) summarises, never deletes. The last 10 messages are always kept verbatim.

**Reddit requests: always include `raw_json=1` and `User-Agent: Weles/0.1`.**
Rate limit: `asyncio.Semaphore(1)` + `asyncio.sleep(1.0)` after each request.

---

## Running the project

```bash
make dev        # Vite dev server + uvicorn with hot reload
make build      # npm run build → FastAPI serves frontend/dist/
make test       # pytest
make lint       # ruff + mypy
make install    # copies .exe + creates Windows startup shortcut (#32)
make package    # PyInstaller build → dist/Weles.exe (#32)
```

Environment (copy `.env.example` → `.env`):
```
ANTHROPIC_API_KEY=   # required
TAVILY_API_KEY=      # optional; web search disabled if absent
WELES_MODEL=claude-sonnet-4-6
WELES_MAX_TOKENS=4096
WELES_DB_PATH=       # defaults to ~/.weles/weles.db
WELES_PORT=8000
WELES_ENV=development
```

---

## Test fixtures (tests/conftest.py)

```python
@pytest.fixture
def mock_claude(mocker) -> MagicMock:
    # patches src.weles.agent.client.get_client
    # stream yields [RawTextDeltaEvent("Test."), RawMessageStopEvent()]

@pytest.fixture
def tmp_db(tmp_path) -> Path:
    # sets WELES_DB_PATH; runs alembic upgrade head

@pytest.fixture
def client(tmp_db) -> TestClient:
    from fastapi.testclient import TestClient
    from src.weles.api.main import app
    with TestClient(app) as c:
        yield c
```

Use `mock_claude` for any test that would otherwise call the Claude API.
Use `pytest-httpx` (`httpx_mock` fixture) for any test that would otherwise call Reddit or Tavily.

---

## SSE event format

```
event: text_delta     data: {"delta": "..."}
event: tool_start     data: {"tool": "search_reddit", "description": "Searching r/BuyItForLife..."}
event: tool_end       data: {"tool": "search_reddit", "result_summary": "Found 8 posts"}
event: tool_error     data: {"tool": "search_reddit", "error": "Request timed out"}
event: done           data: {"session_id": "...", "title": "..."}
event: error          data: {"message": "Claude API unavailable"}
```

---

## Documentation

Three files must stay current. Update them in the same PR that closes the issue — not after.

| File | Update when |
|---|---|
| `CHANGELOG.md` | Every merged issue — add entries under `[Unreleased]` in the correct milestone section |
| `docs/api.md` | Issue adds, removes, or changes any API endpoint or SSE event field |
| `docs/architecture.md` | Issue changes a core pattern, module boundary, data flow, or key invariant |

**CHANGELOG entry rules:**
- Group under `Added`, `Changed`, `Fixed`, or `Removed`
- Lead with the user-visible effect, not the implementation detail
- Reference the issue number in parentheses: `(#14)`
- One entry per meaningful change — not one per file touched

**Example entries:**
```markdown
### Added
- Reddit search tool via public JSON API; no credentials required (#14)
- `POST /sessions/{id}/messages` SSE endpoint; streams token deltas and tool progress (#5)

### Changed
- Session title now derived from first 50 chars of first user message (#5)
```

---

## Issue workflow

1. Read the full issue (title, goal, acceptance criteria, tests, technical notes, dependencies).
2. Check that all dependency issues are merged. If not, branch off the dependency's branch.
3. Branch name: `feat/issue-{N}-{slug}` (e.g. `feat/issue-14-reddit-search`).
4. Implement exactly the acceptance criteria — nothing more. Do not refactor adjacent code.
5. Ship the tests specified in "Tests shipped with this issue". Do not skip them.
6. Update `CHANGELOG.md` and any affected docs (see Documentation section above).
7. `make lint && make test` must pass before opening a PR.
8. Open a PR using the project PR template.

---

## PR workflow

- Title: `feat: #{N} {issue title}` (e.g. `feat: #14 Reddit search tool`)
- Target branch: `main` (or dependency branch if applicable)
- Fill out the PR template (checklist items from the issue's acceptance criteria)
- Every PR must be runnable: `make dev` works after merging
