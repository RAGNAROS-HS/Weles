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

<!-- Issues #2–5 land here as they are merged -->

### v0.2 — Personalization
<!-- Issues #6–12 -->

### v0.3 — Research Engine
<!-- Issues #13–18 -->

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
