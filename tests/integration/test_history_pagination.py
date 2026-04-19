"""Integration tests: GET /history pagination."""

import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from weles.db.connection import get_db


def _seed_history(n: int) -> None:
    conn = get_db()
    for i in range(n):
        conn.execute(
            "INSERT INTO history"
            " (id, item_name, category, domain, status, rating, notes,"
            "  follow_up_due_at, check_in_due_at, created_at)"
            " VALUES (?, ?, 'gear', 'fitness', 'bought', NULL, NULL, NULL, NULL, ?)",
            (str(uuid.uuid4()), f"item-{i}", datetime.utcnow()),
        )
    conn.commit()


def test_history_first_page(client: TestClient, tmp_db: object) -> None:
    _seed_history(75)
    r = client.get("/history?limit=50")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 75
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 50


def test_history_second_page(client: TestClient, tmp_db: object) -> None:
    _seed_history(75)
    r = client.get("/history?limit=50&offset=50")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 75
    assert len(body["items"]) == 25
    assert body["offset"] == 50
