"""Integration tests: GET /sessions/{id}/messages pagination."""
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from weles.db.connection import get_db


def _seed_messages(session_id: str, n: int) -> list[str]:
    """Insert n user messages; return their IDs in chronological order."""
    conn = get_db()
    ids: list[str] = []
    base = datetime.utcnow()
    for i in range(n):
        mid = str(uuid.uuid4())
        ids.append(mid)
        conn.execute(
            "INSERT INTO messages"
            " (id, session_id, role, content, tool_name, is_compressed, created_at)"
            " VALUES (?, ?, 'user', ?, NULL, 0, ?)",
            (mid, session_id, f"msg-{i}", base + timedelta(seconds=i)),
        )
    conn.commit()
    return ids


def test_messages_last_page(client: TestClient, tmp_db: object, mock_claude: object) -> None:
    r = client.post("/sessions")
    session_id = r.json()["id"]
    all_ids = _seed_messages(session_id, 150)

    r = client.get(f"/sessions/{session_id}/messages?limit=100")
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 100
    # Should be the LAST 100 messages (chronologically)
    returned_ids = [m["id"] for m in msgs]
    assert returned_ids == all_ids[50:]


def test_messages_before_id(client: TestClient, tmp_db: object, mock_claude: object) -> None:
    r = client.post("/sessions")
    session_id = r.json()["id"]
    all_ids = _seed_messages(session_id, 150)

    # before_id is the 51st message (index 50); expect first 50 messages
    before_id = all_ids[50]
    r = client.get(f"/sessions/{session_id}/messages?limit=100&before_id={before_id}")
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 50
    returned_ids = [m["id"] for m in msgs]
    assert returned_ids == all_ids[:50]
