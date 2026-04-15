"""Unit tests for correction memory and passive pattern detection (issue #27)."""

import uuid
from datetime import datetime


def _insert_history(conn, item_name: str, domain: str, category: str, status: str) -> None:
    conn.execute(
        "INSERT INTO history (id, item_name, category, domain, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), item_name, category, domain, status, datetime.utcnow()),
    )
    conn.commit()


def test_update_preference_writes_row(tmp_db) -> None:
    """update_preference writes a row with the correct dimension, value, and source."""
    from weles.db.connection import get_db
    from weles.db.profile_repo import update_preference

    update_preference("shopping.footwear", "No minimalist", source="user_explicit")

    conn = get_db()
    row = conn.execute("SELECT * FROM preferences WHERE dimension = 'shopping.footwear'").fetchone()
    assert row is not None
    assert row["value"] == "No minimalist"
    assert row["source"] == "user_explicit"
    assert row["reason"] is None


def test_update_preference_appears_in_profile_block(tmp_db) -> None:
    """Preference row written via update_preference appears in build_profile_block output."""
    from weles.db.profile_repo import get_preferences, update_preference
    from weles.profile.context import build_profile_block
    from weles.profile.models import UserProfile

    update_preference("shopping.footwear", "No minimalist", source="user_explicit")

    prefs = get_preferences()
    block = build_profile_block(UserProfile(), prefs)
    assert block is not None
    assert "No minimalist" in block


async def test_passive_detection_writes_preference_on_three_skips(tmp_db, mocker) -> None:
    """Passive detection writes one preference when ≥3 items are skipped in same domain+category."""
    from weles.api.session_start import run_session_start_checks
    from weles.db.connection import get_db

    mocker.patch("weles.api.session_start.run_proactive_checks", return_value=[])

    conn = get_db()
    for name in ("Boot A", "Boot B", "Boot C"):
        _insert_history(conn, name, "shopping", "footwear", "skipped")

    await run_session_start_checks(conn)

    row = conn.execute("SELECT * FROM preferences WHERE dimension = 'shopping.footwear'").fetchone()
    assert row is not None
    assert row["source"] == "agent_inferred"
    assert "footwear" in row["value"]


async def test_passive_detection_does_not_write_on_two_skips(tmp_db, mocker) -> None:
    """Passive detection writes nothing when fewer than 3 items are skipped."""
    from weles.api.session_start import run_session_start_checks
    from weles.db.connection import get_db

    mocker.patch("weles.api.session_start.run_proactive_checks", return_value=[])

    conn = get_db()
    for name in ("Boot A", "Boot B"):
        _insert_history(conn, name, "shopping", "footwear", "skipped")

    await run_session_start_checks(conn)

    row = conn.execute("SELECT * FROM preferences WHERE dimension = 'shopping.footwear'").fetchone()
    assert row is None
