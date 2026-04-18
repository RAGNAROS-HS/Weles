"""Integration tests: deleting a session cascades to messages and clears in-memory state."""
from fastapi.testclient import TestClient


def test_delete_session_removes_messages(client: TestClient, mock_claude: object) -> None:
    # Create session
    r = client.post("/sessions")
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Send a message so the messages table has rows
    r = client.post(f"/sessions/{session_id}/messages", json={"content": "hello"})
    assert r.status_code == 200

    # Delete the session
    r = client.delete(f"/sessions/{session_id}")
    assert r.status_code == 204

    # Verify messages are gone via DB query
    from weles.db.connection import get_db

    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
    ).fetchone()[0]
    assert count == 0


def test_delete_session_not_in_list(client: TestClient) -> None:
    r = client.post("/sessions")
    assert r.status_code == 201
    session_id = r.json()["id"]

    client.delete(f"/sessions/{session_id}")

    sessions = client.get("/sessions").json()
    ids = [s["id"] for s in sessions]
    assert session_id not in ids


def test_delete_nonexistent_session_returns_404(client: TestClient) -> None:
    r = client.delete("/sessions/does-not-exist")
    assert r.status_code == 404
