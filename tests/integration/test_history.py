from datetime import datetime

from fastapi.testclient import TestClient


def _add(client: TestClient, **kwargs: object) -> dict:
    """Call add_to_history_handler directly with the test DB wired up."""
    from weles.tools.history_tools import add_to_history_handler

    base: dict = {
        "item_name": "Test Item",
        "category": "footwear",
        "domain": "shopping",
        "status": "recommended",
    }
    base.update(kwargs)  # type: ignore[arg-type]
    return add_to_history_handler(base).data  # type: ignore[return-value]


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def test_recommended_weekly_sets_follow_up_due_at(client: TestClient) -> None:
    client.patch("/settings", json={"follow_up_cadence": "weekly"})
    item = _add(client, status="recommended")
    assert item["follow_up_due_at"] is not None
    due = _parse_dt(item["follow_up_due_at"])
    diff = (due - datetime.utcnow()).total_seconds()
    assert 6 * 86400 < diff < 8 * 86400


def test_recommended_cadence_off_leaves_follow_up_null(client: TestClient) -> None:
    client.patch("/settings", json={"follow_up_cadence": "off"})
    item = _add(client, status="recommended")
    assert item["follow_up_due_at"] is None


def test_bought_fitness_sets_check_in_30_days(client: TestClient) -> None:
    item = _add(client, status="bought", domain="fitness")
    assert item["check_in_due_at"] is not None
    due = _parse_dt(item["check_in_due_at"])
    diff = (due - datetime.utcnow()).total_seconds()
    assert 29 * 86400 < diff < 31 * 86400


def test_bought_shopping_sets_check_in_90_days(client: TestClient) -> None:
    item = _add(client, status="bought", domain="shopping")
    assert item["check_in_due_at"] is not None
    due = _parse_dt(item["check_in_due_at"])
    diff = (due - datetime.utcnow()).total_seconds()
    assert 89 * 86400 < diff < 91 * 86400


def test_get_history_domain_filter(client: TestClient) -> None:
    _add(client, domain="shopping", status="bought")
    _add(client, domain="fitness", status="bought")
    resp = client.get("/history?domain=shopping")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["domain"] == "shopping" for i in items)
    assert any(i["domain"] == "shopping" for i in items)


def test_get_history_status_filter(client: TestClient) -> None:
    _add(client, status="recommended")
    _add(client, status="bought")
    resp = client.get("/history?status=recommended")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "recommended" for i in items)


def test_delete_history_item(client: TestClient) -> None:
    item = _add(client, status="bought")
    item_id = item["id"]
    resp = client.delete(f"/history/{item_id}")
    assert resp.status_code == 204
    resp2 = client.delete(f"/history/{item_id}")
    assert resp2.status_code == 404
