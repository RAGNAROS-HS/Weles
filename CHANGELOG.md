# Changelog

All notable changes to Weles are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### v1.1 — Hardening

#### Fixed
- `POST /sessions/{id}/messages` now rejects payloads with `content` exceeding 32,000 chars with HTTP 422 (#78)
- Tool string inputs (item_name, category, notes, value, reason, query) are bounded by `maxLength` in JSON Schema and silently truncated in `dispatch.py` as a safety net (#78)
- History and preference context blocks are wrapped in `<untrusted_data>` tags; system prompt instructs Claude to treat them as data, never as instructions (#79)
- Newlines stripped from `item_name`, `category`, and `notes` at write time in `add_to_history_handler` (#79)

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
- LangSmith tracing: Anthropic client wrapped with `wrap_anthropic`; `stream_response` decorated with `@traceable(run_type="chain")`; `ToolRegistry.adispatch` decorated with `@traceable(run_type="tool")`
- `LANGSMITH_ENDPOINT`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING` added to `.env.example`; tracing is a no-op when `LANGSMITH_TRACING` is absent or false
- `search_web` Claude tool: searches the open web via Tavily API; returns `WebResult` objects classified by domain as `community`, `commercial`, or `unknown`; results sorted community-first (#16)
- Domain lists (`community_domains.txt`, `commercial_domains.txt`) preloaded at startup via `resource_path`; cached in module-level sets (#16)
- `search_web` registered in `ToolRegistry` only when `TAVILY_API_KEY` is set; absent key → tool not registered, no crash (#16)
- `score_result(RedditPost | WebResult) -> CredibilityLabel` in `research/credibility.py`; labels `high`, `medium`, `low`, `flagged` (#17)
- Reddit scoring: score thresholds (low < 20, medium 20–99, high ≥ 100) with one-tier promotion for ownership-language and "switched from" patterns (#17)
- Web scoring: community domains → `high`, commercial → `low`, unknown → `medium`; affiliate URL patterns (`?ref=`, `/go/`, etc.) → `flagged` regardless of source type (#17)
- `score_results()` batch function: appends `credibility` to each result; sets `batch_flag="coordinated_positivity"` when ≥ 3 low/flagged results share a 4-word n-gram (#17)
- Research prompt updated: Claude instructed to discount `low`/`flagged` results and surface astroturfing warning when `coordinated_positivity` is set (#17)
- Research synthesis guidelines in `research.md`: signal strength labels (`[strong consensus]` / `[divided community]` / `[thin data]`), dissenting views, age/discontinuation flags, no manufacturer language, reasoning over conclusions (#18)
- Research guidelines injected into user turn as a text block on first `search_reddit` or `search_web` call; injected once per stream (#18)
- Tool failure notice sent to Claude after each tool batch: lists failed tool names; Claude instructed to continue and state which sources were unavailable (#18)
- `ToolErrorEvent(tool="max_tool_calls", error="Research limit reached")` emitted when limit exceeded; sentinel `"Research limit reached. Synthesise with what you have."` sent to Claude (#18)
- `scripts/eval_research.py`: runs 5 representative queries against live Claude for manual synthesis quality review; not a CI test (#18)

### Fixed
- Reddit requests returning 403: switched `User-Agent` from `Weles/0.1` to a Chrome browser string; added `Accept` and `Accept-Language` headers
- `GeneratorExit` error logged in LangSmith traces: removed early `break` on `DoneEvent` in the SSE router so `stream_response` exhausts naturally instead of being closed mid-flight

### v0.4 — Domain Modules

#### Added
- Shopping mode prompt (`prompts/modes/shopping.md`): sub-intent classification (category_research, product_lookup, comparative, buy_timing), tool-use sequence, response structures per intent, profile filters for budget_psychology / aesthetic_style / country (#19)
- Diet mode prompt (`prompts/modes/diet.md`): sub-intent classification (meal_suggestion, approach_validation, supplement_guidance, recipe_sourcing), tool-use sequences, response structures per intent (#20)
- Dietary restrictions hard constraint injected into diet mode system prompt when `dietary_restrictions` is set in profile; constraint instructs Claude to discard non-compliant research results (#20)
- Fitness mode prompt (`prompts/modes/fitness.md`): sub-intent classification (program_recommendation, program_check_in, troubleshoot, gear_advice), tool-use sequences, response structures per intent (#21)
- `config/programs.toml` populated with 6 community-vetted programs (5/3/1, GZCLP, Starting Strength, PHUL, C25K, Bodyweight Fitness RR) with level/goal/equipment/source metadata (#21)
- `filter_programs(level, goal, equipment)` in `research/programs.py`; loaded via `resource_path` (#21)
- Programs list and injury_history flag injected into fitness mode system prompt when profile fields are set (#21)
- Lifestyle mode prompt (`prompts/modes/lifestyle.md`): sub-intent classification (product_ecosystem, maintenance_care, organisation, routine), tool-use sequences with web-search fallback, anti-trend enforcement (sustained-use bias, source age always flagged), profile filters for living_situation / climate (#22)

### v0.5 — Learning Loop

#### Added
- `CONTEXT_WINDOW = 200_000` constant and `estimated_tokens(messages)` in `agent/session.py`; word-count × 1.3 approximation (#23)
- `Session.get_messages_for_context()`: returns messages as role/content dicts for the Claude API, stripping internal tracking fields; compressed messages are returned with their already-substituted summary content (#23)
- `compress_tool_results(session_id, client, turn_messages)` in `agent/compression.py`: replaces tool_result block content with a 2-sentence Claude summary; fire-and-forget, does not block the stream (#23)
- `maybe_compress_context(session_id, client, session)` in `agent/compression.py`: when `estimated_tokens > 0.8 × CONTEXT_WINDOW`, summarises the oldest 25% of user+assistant pairs; the last 10 messages are never touched; updates DB and in-memory session (#23)
- Context compression triggered as a background task after every SSE turn in `api/routers/messages.py` (#23)

#### Added
- `run_session_start_checks(db)` in `api/session_start.py`: orchestrates all session-start checks in order — passive pattern detection, decay, follow-up, check-in; returns `SessionStartResult{prompt, notices}`; at most one user-facing prompt (#24)
- Passive pattern detection writes `preferences` row with `source="agent_inferred"` when ≥3 history items are skipped in the same domain+category (#24)
- `check_follow_up(db) -> SessionStartPrompt | None` in `api/session_start.py`; queries oldest overdue recommended item; returns `follow_up` prompt or `None` (#25)
- `snooze_follow_up(item_id, cadence_days)` in `history_repo.py`; `snooze_follow_up` Claude tool registered in registry (#25)
- `check_check_in(db) -> SessionStartPrompt | None` in `api/session_start.py`; queries oldest overdue bought/tried item; returns `check_in` prompt or `None` (#26)
- `snooze_check_in(item_id, days=30)` in `history_repo.py`; `snooze_check_in` Claude tool registered in registry for "Remind me later" response (#26)
- `update_preference(dimension, value, reason, source)` in `profile_repo.py`; upserts a preference row (#27)
- `update_preference` Claude tool in `tools/profile_tools.py`; registered in `ToolRegistry`; source always `"user_explicit"` (#27)
- System prompt instructs Claude to call `update_preference` immediately on user pushback (#27)
- Passive pattern detection updated: dimension `{domain}.{category}`, value describes skipping pattern, delegates to `update_preference` (#27)
- `check_decay(profile, thresholds) -> DecayPrompt | None` in `profile/decay.py`; returns prompt for most-overdue stale field; only non-null fields evaluated (#28)
- `FIELD_DECAY_CATEGORY` mapping moved to `profile/decay.py`; `_step2_decay_check` in session_start delegates to `check_decay` (#28)

#### Changed
- `POST /sessions` returns `session_start_prompt: {prompt, notices}` from the orchestrator instead of a static `null` (#24)

#### Fixed
- `tool_result` blocks now appear before `text` blocks in user messages following a tool-use turn; previous ordering caused `BadRequestError` from the Anthropic API (#23)

### v0.6 — Signal Quality

#### Added
- `research.md` updated with explicit confidence calibration: responses must open with `[strong consensus]`, `[divided community]`, or `[thin data]`; each label defined with criteria (#29)
- `[thin data]` format specified; minority opinion, data age, and discontinued product flags required (#29)
- `scripts/eval_confidence.py`: runs 5 scenario queries for manual confidence label review; not a CI gate (#29)
- `score_results` extended: tags `affiliate: True` on web results with affiliate URLs; geo-block filter tags `available: False` when domain is in `config/geo_blocks/{COUNTRY}.txt` and user country matches (#30)
- Coordinated positivity detection extended: also fires when ≥3 low/flagged results all contain a shared astroturfing phrase (e.g. "exceeded my expectations") (#30)
- `search_web_handler` and `search_reddit_handler` now call `score_results`; all credibility metadata present in results passed to Claude (#30)
- `run_proactive_checks()` added as step 5 of the session-start orchestrator: checks the 5 most recent bought/tried items for Reddit quality-issue discussion (score > 50, cached 24 h per item) and surfaces seasonal notices from `config/seasonal.toml` when the user has domain history (#31)
- `config/seasonal.toml` populated with four seasonal entries (fitness/January–February, shopping/November–December, diet/June–August, lifestyle/March–April) (#31)

### Bug fixes

#### Added
- DB indices for `messages.session_id`, `history.domain`, `history.status`, `history.follow_up_due_at`, `history.check_in_due_at`, and `preferences.dimension` via Alembic migration `002_add_indices` (#75)
- In-memory session cache replaced with an LRU cache capped at 50 sessions (configurable via `WELES_SESSION_CACHE_SIZE`); oldest session is evicted when the limit is exceeded (#76)
- `GET /history` now returns a paginated envelope `{items, total, limit, offset}`; supports `limit` and `offset` query params (default 50/0) (#77)
- `GET /sessions/{id}/messages` supports `limit` (default 100) and `before_id` cursor for loading older messages (#77)
- History page shows "Load more" button when more items exist beyond the first page (#77)
- Chat loads last 100 messages on session select; "Load older messages" button prepends the preceding 100 (#77)

#### Fixed
- Information tab content is now scrollable when it exceeds the viewport height; settings page receives the same fix (#68)
- Tool call limit check now fires before the handler executes; counter checked with `>=` before increment so exactly `max_tool_calls_per_turn` calls are permitted (#70)
- `get_all_settings()` and `get_setting()` no longer crash on corrupt JSON in the settings table — bad rows are skipped with a warning (#71)
- `set_setting()` validates value types for user-configurable keys; raises `ValueError` on invalid input, which the settings router converts to HTTP 422 (#71)
- Deleting a session now cascades to remove all its messages (FK constraint was already in schema; `PRAGMA foreign_keys = ON` was already in connection); in-memory session cache is also evicted on delete (#72)
- Context compression now matches messages by ID instead of content; previously two messages with identical text could cause the wrong one to be overwritten (#73)
- SSE data-line parsing now wraps `JSON.parse` in try-catch; a malformed event no longer terminates the stream handler (#74)
- All `api.ts` fetch calls now check `r.ok` before calling `.json()`; HTTP errors throw instead of crashing silently as parse errors (#74)
- Settings, Information, and History pages show "Failed to load — try refreshing" instead of spinning "Loading…" indefinitely when the backend is unreachable (#74)
- Null response body (network failure before headers complete) now removes the frozen assistant placeholder and shows "Connection failed — try again" (#74)
- `newChat()` preserves the currently selected mode instead of always resetting to `general` (#74)

### v1.0 — Distribution

#### Added
- `src/weles/tray.py`: system tray entry point using `pystray`; starts the FastAPI server in a daemon thread, left-click opens browser, right-click menu has Open / Restart server / Quit (#32)
- Auto-opens browser on first launch (`GET /health` → `first_run: true`); waits for server to be ready before opening (#32)
- Port conflict detection at startup: tooltip shows "Port {port} already in use"; right-click menu adds "Change port" which persists `WELES_PORT` to `~/.weles/.env` (#32)
- `weles.spec`: PyInstaller spec committed; bundles `frontend/dist`, `config`, `prompts`, `blocklist`, `assets` into a single `console=False` `Weles.exe` (#32)
- `make package`: runs `npm run build` then `pyinstaller weles.spec --clean` → `dist/Weles.exe` (#32)
- `make install`: copies `dist/Weles.exe` to `%LOCALAPPDATA%\Weles\Weles.exe` and creates a `.lnk` startup shortcut in the Windows Startup folder; no admin rights required (#32)
- `make uninstall`: removes the startup shortcut; does not touch `~/.weles/` data (#32)
- `.github/workflows/build-windows.yml`: triggers on `tags: v*.*.*`; runs `make package` on `windows-latest`; uploads `dist/Weles.exe` as a GitHub release asset (#32)

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
