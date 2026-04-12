from fastapi.testclient import TestClient


def test_get_history_context_no_items_returns_none(client: TestClient) -> None:
    from weles.db.history_repo import get_history_context

    result = get_history_context("shopping")
    assert result is None


def test_get_history_context_with_items_contains_names(client: TestClient) -> None:
    from weles.db.history_repo import add_to_history, get_history_context

    add_to_history("Red Wing 875", "footwear", "shopping", "bought", rating=5)
    add_to_history("Blundstones", "footwear", "shopping", "tried", notes="too narrow")

    result = get_history_context("shopping")
    assert result is not None
    assert "Red Wing 875" in result
    assert "Blundstones" in result
