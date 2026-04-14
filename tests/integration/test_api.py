def test_post_sessions_returns_201(client):
    resp = client.post("/sessions")
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["title"] is None
    assert body["mode"] == "general"
    assert "created_at" in body
    assert body["session_start_prompt"] == {"prompt": None, "notices": []}


def test_get_sessions_empty_on_fresh_db(client):
    resp = client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_session_returns_204_and_messages_404(client):
    session_id = client.post("/sessions").json()["id"]
    resp = client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 204
    resp = client.get(f"/sessions/{session_id}/messages")
    assert resp.status_code == 404


def test_patch_session_mode(client):
    session_id = client.post("/sessions").json()["id"]
    resp = client.patch(f"/sessions/{session_id}", json={"mode": "shopping"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "shopping"


def test_patch_settings_unknown_key_returns_422(client):
    resp = client.patch("/settings", json={"nonexistent_key": "value"})
    assert resp.status_code == 422


def test_patch_settings_valid_key(client):
    resp = client.patch("/settings", json={"follow_up_cadence": "weekly"})
    assert resp.status_code == 200
    assert resp.json()["follow_up_cadence"] == "weekly"


def test_delete_data_returns_204_and_sessions_empty(client):
    client.post("/sessions")
    resp = client.delete("/data")
    assert resp.status_code == 204
    resp = client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == []
