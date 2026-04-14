"""Session start orchestrator.

Runs all session-start checks in order; returns at most one user-facing prompt.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from weles.db.connection import get_db
from weles.db.settings_repo import get_setting

# Maps profile field → decay_thresholds category key
_FIELD_DECAY_CATEGORY: dict[str, str] = {
    "fitness_goal": "goals",
    "dietary_goal": "goals",
    "lifestyle_focus": "goals",
    "fitness_level": "fitness_level",
    "dietary_approach": "dietary_approach",
    "height_cm": "body_metrics",
    "weight_kg": "body_metrics",
    "build": "body_metrics",
    "aesthetic_style": "taste_lifestyle",
    "activity_level": "taste_lifestyle",
    "living_situation": "taste_lifestyle",
    "climate": "taste_lifestyle",
    "budget_psychology": "taste_lifestyle",
}


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
        dimension = f"skip/{row['domain']}/{row['category']}"
        existing = conn.execute(
            "SELECT id FROM preferences WHERE dimension = ?", (dimension,)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            "INSERT INTO preferences (id, dimension, value, reason, source, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                dimension,
                "dislikes",
                f"Skipped {row['cnt']} times in {row['category']}",
                "agent_inferred",
                datetime.utcnow(),
            ),
        )
    conn.commit()


def _step2_decay_check(conn: sqlite3.Connection) -> SessionStartPrompt | None:
    """Return a decay prompt when any tracked profile field is older than its threshold."""
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    if row is None:
        return None
    timestamps: dict[str, str] = json.loads(row["field_timestamps"] or "{}")
    if not timestamps:
        return None

    thresholds_raw = get_setting("decay_thresholds") or {}
    thresholds: dict[str, int] = thresholds_raw if isinstance(thresholds_raw, dict) else {}
    now = datetime.utcnow()

    for field_name, category in _FIELD_DECAY_CATEGORY.items():
        ts_str = timestamps.get(field_name)
        if not ts_str:
            continue
        value = row[field_name]
        if value is None:
            continue
        threshold_days = thresholds.get(category, 365)
        try:
            ts = datetime.fromisoformat(ts_str)
        except ValueError:
            continue
        age_days = (now - ts).days
        if age_days >= threshold_days:
            label = field_name.replace("_", " ")
            return SessionStartPrompt(
                type="decay",
                message=(
                    f"Your {label} was last set {age_days} days ago as '{value}'. Still accurate?"
                ),
            )
    return None


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


def run_session_start_checks(conn: sqlite3.Connection | None = None) -> SessionStartResult:
    """Run all session-start checks in order; return at most one user-facing prompt.

    Execution order:
    1. Passive pattern detection (no prompt; writes inferred preferences)
    2. Profile decay check
    3. Follow-up check (skipped if step 2 produced a prompt)
    4. Check-in check (skipped if step 2 or 3 produced a prompt)
    5. QC / proactive surfacing (notices only; independent of prompt — implemented in #31)
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

    # Step 5: QC / proactive surfacing (notices only) — implemented in #31
    # result.notices = _step5_qc_notices(conn)

    return result
