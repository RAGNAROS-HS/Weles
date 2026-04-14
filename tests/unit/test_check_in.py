"""Unit tests for outcome check-ins: check_check_in function."""

import uuid
from datetime import datetime, timedelta

from weles.api.session_start import check_check_in


def _insert_history_raw(
    conn,
    item_name: str,
    status: str,
    check_in_due_at=None,
) -> None:
    conn.execute(
        "INSERT INTO history"
        " (id, item_name, category, domain, status, check_in_due_at, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            item_name,
            "program",
            "fitness",
            status,
            check_in_due_at,
            datetime.utcnow(),
        ),
    )
    conn.commit()


def test_check_check_in_no_due_items_returns_none(tmp_db) -> None:
    """check_check_in with no due items returns None."""
    from weles.db.connection import get_db

    conn = get_db()
    result = check_check_in(conn)
    assert result is None


def test_check_check_in_due_item_returns_prompt(tmp_db) -> None:
    """check_check_in with a due item returns a check_in prompt containing the item name."""
    from weles.db.connection import get_db

    conn = get_db()
    past = datetime.utcnow() - timedelta(days=1)
    _insert_history_raw(conn, "GZCLP", "bought", check_in_due_at=past)

    result = check_check_in(conn)
    assert result is not None
    assert result.type == "check_in"
    assert "GZCLP" in result.message
