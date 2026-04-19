"""Unit tests: in-memory session cache eviction on delete."""

from weles.agent.session import Session
from weles.api.routers.messages import _sessions, evict_session


def test_evict_session_removes_from_cache() -> None:
    session_id = "test-evict-123"
    _sessions[session_id] = Session()
    assert session_id in _sessions

    evict_session(session_id)

    assert session_id not in _sessions


def test_evict_session_noop_for_unknown_id() -> None:
    # Should not raise for a session that was never loaded
    evict_session("nonexistent-id-xyz")


def test_evict_session_called_on_delete(tmp_db: object) -> None:
    """delete_session endpoint calls evict_session after DB delete."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from weles.api.main import app

    async def _fake_startup(state: object) -> None:
        state.web_search_available = False  # type: ignore[attr-defined]
        state.is_first_run = True  # type: ignore[attr-defined]

    with patch("weles.api.startup.startup", new=_fake_startup), TestClient(app) as client:
        r = client.post("/sessions")
        session_id = r.json()["id"]

        # Manually populate the in-memory cache to simulate a prior request
        _sessions[session_id] = Session()
        assert session_id in _sessions

        client.delete(f"/sessions/{session_id}")

        assert session_id not in _sessions
