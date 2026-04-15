"""Unit tests for the session start orchestrator."""

import json
import uuid
from datetime import datetime, timedelta

from weles.api.session_start import run_session_start_checks


def _insert_history(
    conn,
    item_name: str,
    domain: str,
    category: str,
    status: str,
    follow_up_due_at=None,
    check_in_due_at=None,
) -> None:
    conn.execute(
        "INSERT INTO history"
        " (id, item_name, category, domain, status, follow_up_due_at, check_in_due_at, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            item_name,
            category,
            domain,
            status,
            follow_up_due_at,
            check_in_due_at,
            datetime.utcnow(),
        ),
    )
    conn.commit()


def _set_profile_field_with_timestamp(conn, field_name: str, value: str, days_ago: int) -> None:
    ts = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
    existing = conn.execute("SELECT id FROM profile WHERE id = 1").fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO profile (id, field_timestamps) VALUES (1, ?)",
            (json.dumps({field_name: ts}),),
        )
    else:
        profile = conn.execute("SELECT field_timestamps FROM profile WHERE id = 1").fetchone()
        timestamps = json.loads(profile["field_timestamps"] or "{}")
        timestamps[field_name] = ts
        conn.execute(
            "UPDATE profile SET field_timestamps = ? WHERE id = 1",
            (json.dumps(timestamps),),
        )
    conn.execute(f"UPDATE profile SET {field_name} = ? WHERE id = 1", (value,))  # noqa: S608
    conn.commit()


async def test_no_due_items_returns_empty(tmp_db) -> None:
    """With no due items, returns {prompt: None, notices: []}."""
    from weles.db.connection import get_db

    conn = get_db()
    result = await run_session_start_checks(conn)
    assert result.prompt is None
    assert result.notices == []


async def test_decay_wins_over_followup(tmp_db, mocker) -> None:
    """With decay due AND follow-up due, decay prompt is returned (decay wins)."""
    from weles.db.connection import get_db

    mocker.patch("weles.api.session_start.run_proactive_checks", return_value=[])

    conn = get_db()
    # Fitness level set 200 days ago (threshold = 90 days)
    _set_profile_field_with_timestamp(conn, "fitness_level", "beginner", 200)
    # Follow-up also due
    past = datetime.utcnow() - timedelta(days=1)
    _insert_history(
        conn, "Running Shoes", "shopping", "footwear", "recommended", follow_up_due_at=past
    )

    result = await run_session_start_checks(conn)
    assert result.prompt is not None
    assert result.prompt.type == "decay"


async def test_followup_wins_over_checkin(tmp_db, mocker) -> None:
    """With follow-up due AND check-in due, follow-up prompt is returned."""
    from weles.db.connection import get_db

    mocker.patch("weles.api.session_start.run_proactive_checks", return_value=[])

    conn = get_db()
    past = datetime.utcnow() - timedelta(days=1)
    _insert_history(
        conn, "Foam Roller", "fitness", "recovery", "recommended", follow_up_due_at=past
    )
    _insert_history(conn, "GZCLP", "fitness", "program", "bought", check_in_due_at=past)

    result = await run_session_start_checks(conn)
    assert result.prompt is not None
    assert result.prompt.type == "follow_up"


async def test_checkin_when_only_due(tmp_db, mocker) -> None:
    """With only a check-in due, check-in prompt is returned."""
    from weles.db.connection import get_db

    mocker.patch("weles.api.session_start.run_proactive_checks", return_value=[])

    conn = get_db()
    past = datetime.utcnow() - timedelta(days=1)
    _insert_history(conn, "Starting Strength", "fitness", "program", "bought", check_in_due_at=past)

    result = await run_session_start_checks(conn)
    assert result.prompt is not None
    assert result.prompt.type == "check_in"


async def test_passive_detection_writes_preference(tmp_db, mocker) -> None:
    """Passive detection writes a preference when ≥3 items skipped in the same category."""
    from weles.db.connection import get_db

    mocker.patch("weles.api.session_start.run_proactive_checks", return_value=[])

    conn = get_db()
    for i in range(3):
        _insert_history(conn, f"Keto Bar {i}", "diet", "keto_snacks", "skipped")

    await run_session_start_checks(conn)

    pref = conn.execute(
        "SELECT * FROM preferences WHERE dimension = ?", ("diet.keto_snacks",)
    ).fetchone()
    assert pref is not None
    assert "keto_snacks" in pref["value"]
    assert pref["source"] == "agent_inferred"


async def test_passive_detection_returns_no_prompt(tmp_db, mocker) -> None:
    """Passive pattern detection does not produce a user-facing prompt."""
    from weles.db.connection import get_db

    mocker.patch("weles.api.session_start.run_proactive_checks", return_value=[])

    conn = get_db()
    for i in range(3):
        _insert_history(conn, f"Supplement {i}", "diet", "supplements", "skipped")

    result = await run_session_start_checks(conn)
    assert result.prompt is None
