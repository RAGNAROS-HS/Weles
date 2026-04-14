"""Integration tests for preferences API (issue #27)."""

import uuid
from datetime import datetime


def _insert_preference(client) -> str:
    """Insert a preference directly into the DB and return its id."""
    from weles.db.connection import get_db

    pref_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO preferences (id, dimension, value, reason, source, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (pref_id, "shopping.footwear", "No minimalist", None, "user_explicit", datetime.utcnow()),
    )
    conn.commit()
    return pref_id


def test_delete_preference_removes_row(client) -> None:
    """DELETE /preferences/{id} removes the row; GET /preferences no longer lists it."""
    pref_id = _insert_preference(client)

    # Confirm it's there
    resp = client.get("/preferences")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert pref_id in ids

    # Delete it
    resp = client.delete(f"/preferences/{pref_id}")
    assert resp.status_code == 204

    # Confirm it's gone
    resp = client.get("/preferences")
    ids = [p["id"] for p in resp.json()]
    assert pref_id not in ids
