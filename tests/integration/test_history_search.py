"""Integration tests: GET /history search and sort params."""

import uuid
from datetime import datetime, timedelta

from weles.db.connection import get_db


def _insert(
    conn,
    item_name: str,
    domain: str = "shopping",
    status: str = "recommended",
    created_at: datetime | None = None,
) -> None:
    conn.execute(
        "INSERT INTO history (id, item_name, category, domain, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), item_name, "audio", domain, status, created_at or datetime.utcnow()),
    )
    conn.commit()


def test_search_filters_by_name(client) -> None:
    conn = get_db()
    _insert(conn, "Sony WH-1000XM5")
    _insert(conn, "Bose QC45")
    r = client.get("/history?search=sony")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["item_name"] == "Sony WH-1000XM5"


def test_search_is_case_insensitive(client) -> None:
    conn = get_db()
    _insert(conn, "Sony WH-1000XM5")
    _insert(conn, "Bose QC45")
    r = client.get("/history?search=SONY")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["item_name"] == "Sony WH-1000XM5"


def test_sort_oldest_returns_ascending(client) -> None:
    conn = get_db()
    now = datetime.utcnow()
    _insert(conn, "Old item", created_at=now - timedelta(days=10))
    _insert(conn, "New item", created_at=now)
    r = client.get("/history?sort=oldest")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 2
    assert items[0]["item_name"] == "Old item"


def test_search_composes_with_domain(client) -> None:
    conn = get_db()
    _insert(conn, "Sony WH-1000XM5", domain="shopping")
    _insert(conn, "Sony protein bar", domain="diet")
    r = client.get("/history?search=sony&domain=shopping")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["domain"] == "shopping"


def test_search_composes_with_status(client) -> None:
    conn = get_db()
    _insert(conn, "Sony WH-1000XM5", status="recommended")
    _insert(conn, "Sony LinkBuds", status="bought")
    r = client.get("/history?search=sony&status=bought")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["item_name"] == "Sony LinkBuds"
