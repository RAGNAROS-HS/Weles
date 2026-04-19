# Weles

A locally-hosted personal AI agent that advises on shopping, lifestyle, diet, and fitness. All advice is grounded in community consensus — Reddit threads, long-term owner reports, enthusiast forums — never manufacturer claims or affiliate copy.

Weles builds a persistent profile of you and applies it to every response. It runs entirely on your machine as a Windows desktop app (system tray + browser UI) backed by a local SQLite database.

---

## Features

### Modes

Switch between five advisory modes using the tab bar. The agent routes its research and prompt to the appropriate domain.

| Mode | What it does |
|---|---|
| **General** | Open-ended questions; no domain-specific routing |
| **Shopping** | Community consensus picks, long-term owner opinions, failure modes, buy-timing advice |
| **Diet** | Meal suggestions, supplement guidance (community experience only), what people actually sustain |
| **Fitness** | Program recommendations, troubleshooting, community-vetted routines |
| **Lifestyle** | Home, organization, routines — durable consensus vs. hype cycles |

### Persistent profile

The agent builds a profile of you across conversations and applies it to every response. It captures:

- Body: height, weight, build, fitness level, injury history
- Dietary: restrictions, preferences, current approach
- Taste: aesthetic style, brand rejections
- Lifestyle: climate, activity level, living situation
- Budget psychology: "buy once buy right" vs "good enough for now"
- Goals: current fitness, dietary, and lifestyle focus

Profile fields are inferred from conversation when possible. Missing fields for the active mode are asked for at most one at a time — no onboarding form.

Fields older than configurable thresholds are flagged as stale; the agent asks to reconfirm before acting on them.

### Research — community sources only

The anti-marketing principle: no manufacturer spec sheets, no affiliate listicles, no influencer content. Sources ranked by signal quality:

1. Reddit (primary) — targeted subreddit routing by mode and subcategory
2. Hobbyist / enthusiast forums (secondary)
3. Subreddit wikis and FAQ stickies
4. General web via Tavily (last resort; optional)

Signal sought: "I've owned this for X years" posts, recurring failure modes, what people switched to and why, price-to-longevity patterns.

Subreddits are routed by mode and subcategory from `config/subreddits.toml`. Examples:

- Shopping → r/BuyItForLife, r/frugalmalefashion, category-specific (r/headphones, r/Coffee, etc.)
- Diet → r/nutrition, r/EatCheapAndHealthy, approach-specific (r/keto, r/veganfitness, etc.)
- Fitness → r/Fitness, r/weightroom, r/bodyweightfitness, r/running
- Lifestyle → r/minimalism, r/organization, r/BuyItForLife

### History tracking

Items you've been recommended, bought, tried, or returned are stored. The agent tracks follow-up and check-in dates, surfaces outcomes after time has passed, and adjusts future recommendations based on what you've reported.

### Context compression

Long conversations are automatically summarised when context approaches the model's limit. The oldest 25% of messages are compressed into 2–3 sentence summaries; the most recent 10 messages are always kept verbatim.

### Session start checks

On each new session, the agent runs a single orchestrated check and surfaces at most one prompt:

1. Passive pattern detection (silent — updates inferred preferences)
2. Profile decay check — asks to reconfirm stale fields
3. Overdue follow-up — "did you end up buying X?"
4. Overdue check-in — "did that work out?"
5. Proactive surfacing — QC issues or seasonal relevance for things you own (shown as dismissable banners)

### LangSmith tracing (optional)

Full observability when `LANGSMITH_TRACING=true`: every Claude API call, the full agent loop, and each tool dispatch are traced as structured spans.

---

## Architecture

```
Browser  ←→  FastAPI (uvicorn)  ←→  Claude API
                  |                      |
               SQLite              Reddit / Tavily
          (~/.weles/weles.db)
```

FastAPI serves both the API and the built React frontend from a single process. In production (as a `.exe`) there is no Node.js — the frontend is a pre-built static bundle mounted at `/`.

### Stack

| Layer | Technology |
|---|---|
| LLM | Claude API (`claude-sonnet-4-6`), raw Anthropic SDK, tool_use pattern |
| Backend | FastAPI + SSE streaming |
| Frontend | React + Vite + TypeScript |
| Storage | SQLite at `~/.weles/weles.db`, WAL mode, Alembic migrations |
| Reddit | `httpx` → public JSON API, no credentials required |
| Web search | Tavily API; gracefully absent when key not set |
| Packaging | `pystray` system tray + PyInstaller `.exe` + Windows startup folder |
| Deps | `uv` |

### Agent loop

1. User message saved to DB
2. System prompt built: `system.md` + mode-specific prompt + serialised profile + preferences
3. Missing profile fields and domain history context injected into the user turn
4. `stream_response()` called — yields typed `AgentEvent`s streamed as SSE to the browser
5. Tool calls dispatched via `ToolRegistry`; capped at `max_tool_calls_per_turn` (default: 6)
6. On completion: assistant reply saved to DB; context compressed in background if needed

### SSE event types

```
text_delta    {"delta": "..."}
tool_start    {"tool": "...", "description": "..."}
tool_end      {"tool": "...", "result_summary": "..."}
tool_error    {"tool": "...", "error": "..."}
done          {"session_id": "...", "title": "..."}
error         {"message": "..."}
```

`tool_error` never aborts the stream. `error` (Claude API failure) does.

### Database schema

Six tables, created in a single Alembic migration:

| Table | Purpose |
|---|---|
| `sessions` | Chat sessions: id, title, mode, created_at |
| `messages` | All messages: role, content, tool_name, is_compressed |
| `profile` | Single row: all profile fields + per-field timestamps |
| `history` | Items recommended/tried: follow_up_due_at, check_in_due_at |
| `preferences` | Learned preferences: dimension, value, source (explicit / inferred) |
| `settings` | Key-value config: cadences, thresholds, tool call cap |

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- [`uv`](https://github.com/astral-sh/uv) — `pip install uv`
- An Anthropic API key (required)
- A Tavily API key (optional — enables web search)

### Install dependencies

```bash
uv sync
cd frontend && npm install
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...     # required
TAVILY_API_KEY=tvly-...          # optional; web search disabled if absent
WELES_MODEL=claude-sonnet-4-6
WELES_MAX_TOKENS=4096
WELES_DB_PATH=                   # defaults to ~/.weles/weles.db
WELES_PORT=8000
WELES_ENV=development
```

---

## Running

### Development (hot reload)

```bash
make dev
```

Starts Vite dev server on `http://localhost:5173` and uvicorn on `http://localhost:8000` with hot reload.

### Production build

```bash
make build    # compiles React to frontend/dist/
uv run uvicorn src.weles.api.main:app --port 8000
```

FastAPI serves the compiled frontend at `/`. Open `http://localhost:8000`.

### Windows desktop app

Build the standalone `.exe`:

```bash
make package
```

Install to `%LOCALAPPDATA%\Weles\` and add a Windows startup shortcut:

```bash
make install
```

The app runs as a system tray icon. Left-click opens the browser UI. The server starts automatically on login.

To uninstall:

```bash
make uninstall
```

---

## Commands

| Command | Description |
|---|---|
| `make dev` | Vite dev server + uvicorn with hot reload |
| `make build` | Compile frontend to `frontend/dist/` |
| `make test` | Run pytest |
| `make lint` | ruff format check + ruff lint + mypy |
| `make package` | Build `dist/Weles.exe` via PyInstaller |
| `make install` | Copy `.exe` and create Windows startup shortcut |
| `make uninstall` | Remove startup shortcut |

---

## Testing

```bash
make test
# or
uv run pytest tests/ -q
```

The test suite uses:
- `pytest-mock` for Anthropic SDK mocking
- `pytest-httpx` for Reddit and Tavily HTTP mocking
- `tmp_db` fixture for an isolated in-memory SQLite per test

---

## LangSmith tracing

Add to `.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls__...
LANGSMITH_PROJECT=weles
# For EU region:
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```

Three trace layers: every Claude API call, the full agent loop, and each tool dispatch as individual spans.

---

## Data export

Export all your data (profile, preferences, history) from the UI settings panel as JSON or CSV. Clear all data via `DELETE /data` (re-runs Alembic migrations).

---

## Configuration

Runtime settings stored in the `settings` table, editable from the UI:

| Setting | Default | Description |
|---|---|---|
| `max_tool_calls_per_turn` | `6` | Cap on research calls per message |
| `follow_up_cadence` | — | Days until follow-up prompts surface |
| `check_in_cadence` | — | Days until check-in prompts surface |
| `decay_thresholds` | — | Days until profile fields are considered stale |
| `proactive_surfacing` | — | Whether to surface QC/seasonal notices |
