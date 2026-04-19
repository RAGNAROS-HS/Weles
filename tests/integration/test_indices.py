"""Integration test: all expected indices exist after alembic upgrade head."""

from weles.db.connection import get_db

EXPECTED_INDICES = {
    "idx_messages_session_id",
    "idx_history_domain",
    "idx_history_status",
    "idx_history_follow_up_due",
    "idx_history_check_in_due",
    "idx_preferences_dimension",
}


def test_all_indices_exist(tmp_db: object) -> None:
    conn = get_db()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    existing = {row["name"] for row in rows}
    assert existing >= EXPECTED_INDICES, f"Missing indices: {EXPECTED_INDICES - existing}"
