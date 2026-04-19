"""Unit tests for edge cases in the messages SSE stream handler."""

import json
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_empty_history_yields_error_event(tmp_db, mocker) -> None:
    from fastapi.testclient import TestClient

    from weles.api.main import app

    mocker.patch(
        "weles.api.routers.messages._load_history",
        return_value=[],
    )

    async def _fake_startup(state: object) -> None:
        state.web_search_available = False  # type: ignore[attr-defined]
        state.is_first_run = True  # type: ignore[attr-defined]

    with patch("weles.api.startup.startup", new=_fake_startup), TestClient(app) as client:
        resp = client.post("/sessions")
        assert resp.status_code == 201
        session_id = resp.json()["id"]

        events = []
        with client.stream(
            "POST",
            f"/sessions/{session_id}/messages",
            json={"content": "hello"},
            headers={"Accept": "text/event-stream"},
        ) as r:
            for line in r.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[len("data:") :].strip()))
                elif line.startswith("event:"):
                    events.append({"_event": line[len("event:") :].strip()})

    error_events = [e for e in events if e.get("message") == "No messages found for session"]
    assert len(error_events) == 1
