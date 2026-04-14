"""Unit tests for post-recommendation follow-up: check_follow_up and cadence behavior."""

import uuid
from datetime import datetime, timedelta

from weles.api.session_start import check_follow_up
from weles.db.history_repo import add_to_history
from weles.db.settings_repo import set_setting


def _insert_history_raw(conn, item_name: str, status: str, follow_up_due_at=None) -> None:
    conn.execute(
        "INSERT INTO history"
        " (id, item_name, category, domain, status, follow_up_due_at, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            item_name,
            "gear",
            "shopping",
            status,
            follow_up_due_at,
            datetime.utcnow(),
        ),
    )
    conn.commit()


def test_check_follow_up_no_due_items_returns_none(tmp_db) -> None:
    """check_follow_up with no due items returns None."""
    from weles.db.connection import get_db

    conn = get_db()
    result = check_follow_up(conn)
    assert result is None


def test_check_follow_up_due_item_returns_prompt(tmp_db) -> None:
    """check_follow_up with a due item returns a follow_up prompt with the item name."""
    from weles.db.connection import get_db

    conn = get_db()
    past = datetime.utcnow() - timedelta(days=1)
    _insert_history_raw(conn, "Foam Roller", "recommended", follow_up_due_at=past)

    result = check_follow_up(conn)
    assert result is not None
    assert result.type == "follow_up"
    assert "Foam Roller" in result.message


def test_follow_up_due_at_null_when_cadence_off(tmp_db) -> None:
    """follow_up_due_at is None when follow_up_cadence setting is 'off'."""
    from weles.db.connection import get_db

    set_setting("follow_up_cadence", "off")
    item = add_to_history(
        item_name="Running Shoes",
        category="footwear",
        domain="shopping",
        status="recommended",
    )
    assert item["follow_up_due_at"] is None

    conn = get_db()
    result = check_follow_up(conn)
    assert result is None


def test_follow_up_due_at_set_to_7_days_when_cadence_weekly(tmp_db) -> None:
    """follow_up_due_at is set ~7 days from now when follow_up_cadence is 'weekly'."""
    set_setting("follow_up_cadence", "weekly")
    item = add_to_history(
        item_name="Kettlebell",
        category="equipment",
        domain="fitness",
        status="recommended",
    )
    due = item["follow_up_due_at"]
    assert due is not None
    # Parse the due date and check it's approximately 7 days from now
    due_dt = datetime.fromisoformat(str(due))
    delta = due_dt - datetime.utcnow()
    assert 6 <= delta.days <= 7
