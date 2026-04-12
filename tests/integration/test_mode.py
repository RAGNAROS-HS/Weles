from fastapi.testclient import TestClient


def test_patch_session_valid_mode(client: TestClient) -> None:
    resp = client.post("/sessions")
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    resp = client.patch(f"/sessions/{session_id}", json={"mode": "shopping"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "shopping"


def test_patch_session_invalid_mode(client: TestClient) -> None:
    resp = client.post("/sessions")
    session_id = resp.json()["id"]

    resp = client.patch(f"/sessions/{session_id}", json={"mode": "invalid"})
    assert resp.status_code == 422
