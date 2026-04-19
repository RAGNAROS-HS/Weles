import pytest


@pytest.mark.usefixtures("mock_claude")
def test_content_too_long_returns_422(client):
    resp = client.post(
        "/sessions",
        json={"mode": "general"},
    )
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    resp = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "x" * 33_000},
    )
    assert resp.status_code == 422


@pytest.mark.usefixtures("mock_claude")
def test_content_at_limit_accepted(client):
    resp = client.post(
        "/sessions",
        json={"mode": "general"},
    )
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    with client.stream(
        "POST",
        f"/sessions/{session_id}/messages",
        json={"content": "x" * 32_000},
    ) as resp:
        assert resp.status_code == 200
