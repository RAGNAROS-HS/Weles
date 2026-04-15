"""Session start orchestrator.

Runs all session-start checks in order; returns at most one user-facing prompt.
"""

from __future__ import annotations

import logging
import sqlite3
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from weles.db.connection import get_db
from weles.db.profile_repo import get_profile, update_preference
from weles.db.settings_repo import get_setting, set_setting
from weles.profile.decay import check_decay
from weles.profile.models import UserProfile
from weles.utils.paths import resource_path

logger = logging.getLogger(__name__)


@dataclass
class SessionStartPrompt:
    type: str  # "follow_up" | "check_in" | "decay"
    message: str


@dataclass
class SessionStartResult:
    prompt: SessionStartPrompt | None = None
    notices: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": (
                {"type": self.prompt.type, "message": self.prompt.message} if self.prompt else None
            ),
            "notices": self.notices,
        }


def _step1_passive_patterns(conn: sqlite3.Connection) -> None:
    """Detect skip patterns (≥3 skipped in same domain+category) and write inferred preferences.

    No user-facing prompt is generated.
    """
    rows = conn.execute(
        "SELECT domain, category, COUNT(*) AS cnt FROM history"
        " WHERE status = 'skipped' GROUP BY domain, category HAVING COUNT(*) >= 3"
    ).fetchall()
    for row in rows:
        dimension = f"{row['domain']}.{row['category']}"
        existing = conn.execute(
            "SELECT id FROM preferences WHERE dimension = ?", (dimension,)
        ).fetchone()
        if existing:
            continue
        update_preference(
            dimension=dimension,
            value=f"Consistently skips {row['category']} recommendations in {row['domain']}",
            source="agent_inferred",
        )


def _step2_decay_check(conn: sqlite3.Connection) -> SessionStartPrompt | None:
    """Return a decay prompt for the most-overdue stale profile field."""
    profile = get_profile()
    thresholds_raw = get_setting("decay_thresholds") or {}
    thresholds: dict[str, int] = thresholds_raw if isinstance(thresholds_raw, dict) else {}
    result = check_decay(profile, thresholds)
    if result is None:
        return None
    return SessionStartPrompt(type=result.type, message=result.message)


def check_follow_up(conn: sqlite3.Connection | None = None) -> SessionStartPrompt | None:
    """Return a follow-up prompt when a recommended item has passed its follow_up_due_at.

    Queries: SELECT * FROM history WHERE status='recommended'
             AND follow_up_due_at <= now() ORDER BY follow_up_due_at ASC LIMIT 1
    """
    if conn is None:
        conn = get_db()
    now = datetime.utcnow()
    row = conn.execute(
        "SELECT * FROM history WHERE status = 'recommended'"
        " AND follow_up_due_at IS NOT NULL AND follow_up_due_at <= ?"
        " ORDER BY follow_up_due_at ASC LIMIT 1",
        (now,),
    ).fetchone()
    if row is None:
        return None
    return SessionStartPrompt(
        type="follow_up",
        message=f"Did you end up getting {row['item_name']}?",
    )


def _step3_followup_check(conn: sqlite3.Connection) -> SessionStartPrompt | None:
    return check_follow_up(conn)


def check_check_in(conn: sqlite3.Connection | None = None) -> SessionStartPrompt | None:
    """Return a check-in prompt when a bought/tried item has passed its check_in_due_at.

    Queries: SELECT * FROM history WHERE status IN ('bought','tried')
             AND check_in_due_at <= now() ORDER BY check_in_due_at ASC LIMIT 1
    """
    if conn is None:
        conn = get_db()
    now = datetime.utcnow()
    row = conn.execute(
        "SELECT * FROM history WHERE status IN ('bought', 'tried')"
        " AND check_in_due_at IS NOT NULL AND check_in_due_at <= ?"
        " ORDER BY check_in_due_at ASC LIMIT 1",
        (now,),
    ).fetchone()
    if row is None:
        return None
    verb = "bought" if row["status"] == "bought" else "started"
    try:
        created = datetime.fromisoformat(str(row["created_at"]))
        days = (now - created).days
    except (ValueError, TypeError):
        days = 0
    return SessionStartPrompt(
        type="check_in",
        message=f"It's been {days} days since you {verb} {row['item_name']}. How's it going?",
    )


def _step4_checkin_check(conn: sqlite3.Connection) -> SessionStartPrompt | None:
    return check_check_in(conn)


async def run_proactive_checks(
    conn: sqlite3.Connection,
    profile: UserProfile,  # noqa: ARG001 — reserved for future profile-aware filtering
) -> list[str]:
    """Return QC alerts and seasonal notices for the current session.

    Returns an empty list immediately if the ``proactive_surfacing`` setting is
    ``"false"``.  Otherwise:

    * Checks the 5 most recent *bought* / *tried* history items for recent
      community quality-issue discussion on Reddit (cached 24 h per item).
    * Surfaces seasonal notices from ``config/seasonal.toml`` when the current
      month matches and the user has any history in the relevant domain.
    """
    from weles.tools.reddit import search_reddit

    if get_setting("proactive_surfacing") == "false":
        return []

    notices: list[str] = []
    now = datetime.utcnow()
    _24h_ago = now - timedelta(hours=24)

    # --- QC monitoring ---
    rows = conn.execute(
        "SELECT id, item_name FROM history"
        " WHERE status IN ('bought', 'tried')"
        " ORDER BY created_at DESC LIMIT 5"
    ).fetchall()

    for row in rows:
        item_id: str = row["id"]
        item_name: str = row["item_name"]
        cache_key = f"qc_cache_{item_id}"

        cached = get_setting(cache_key)
        if cached and isinstance(cached, dict):
            cached_ts_str = cached.get("timestamp")
            if cached_ts_str:
                try:
                    cached_ts = datetime.fromisoformat(cached_ts_str)
                    if cached_ts >= _24h_ago:
                        continue
                except ValueError:
                    pass

        try:
            posts = await search_reddit(
                query=f"{item_name} quality issue OR defect OR recall",
                time_filter="month",
                limit=5,
            )
        except Exception:
            logger.warning("QC search failed for %s", item_name)
            continue

        found = False
        for post in posts:
            if post["score"] > 50:
                found = True
                url = post["url"]
                notices.append(
                    f"Recent community discussion about quality issues with {item_name}: {url}"
                )
                break

        set_setting(cache_key, {"timestamp": now.isoformat(), "found": found})

    # --- Seasonal surfacing ---
    seasonal_path = resource_path("config/seasonal.toml")
    try:
        with open(seasonal_path, "rb") as fh:
            seasonal_data = tomllib.load(fh)
    except (FileNotFoundError, OSError):
        return notices

    current_month = now.month
    for entry in seasonal_data.get("entries", []):
        months: list[int] = entry.get("months", [])
        if current_month not in months:
            continue
        domain: str = entry.get("domain", "")
        if not domain:
            continue
        has_history = conn.execute(
            "SELECT 1 FROM history WHERE domain = ? LIMIT 1", (domain,)
        ).fetchone()
        if has_history:
            notices.append(entry["prompt"])

    return notices


async def run_session_start_checks(
    conn: sqlite3.Connection | None = None,
) -> SessionStartResult:
    """Run all session-start checks in order; return at most one user-facing prompt.

    Execution order:
    1. Passive pattern detection (no prompt; writes inferred preferences)
    2. Profile decay check
    3. Follow-up check (skipped if step 2 produced a prompt)
    4. Check-in check (skipped if step 2 or 3 produced a prompt)
    5. QC / proactive surfacing (notices only; independent of prompt)
    """
    if conn is None:
        conn = get_db()

    result = SessionStartResult()

    _step1_passive_patterns(conn)

    result.prompt = _step2_decay_check(conn)

    if result.prompt is None:
        result.prompt = _step3_followup_check(conn)

    if result.prompt is None:
        result.prompt = _step4_checkin_check(conn)

    profile = get_profile()
    result.notices = await run_proactive_checks(conn, profile)

    return result
