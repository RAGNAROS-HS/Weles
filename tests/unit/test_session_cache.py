"""Tests for LRU session cache in messages router."""

import pytest

import weles.api.routers.messages as messages_mod


@pytest.fixture(autouse=True)
def _clear_sessions():
    """Reset the LRU cache before each test."""
    messages_mod._sessions.clear()
    yield
    messages_mod._sessions.clear()


def test_oldest_evicted_when_cache_full():
    original_size = messages_mod._SESSION_CACHE_SIZE
    messages_mod._SESSION_CACHE_SIZE = 3
    try:
        for i in range(4):
            messages_mod._get_or_create_session(f"session-{i}")
        # session-0 should have been evicted
        assert "session-0" not in messages_mod._sessions
        assert "session-1" in messages_mod._sessions
        assert "session-2" in messages_mod._sessions
        assert "session-3" in messages_mod._sessions
    finally:
        messages_mod._SESSION_CACHE_SIZE = original_size


def test_evict_session_removes_from_cache():
    messages_mod._get_or_create_session("abc")
    assert "abc" in messages_mod._sessions
    messages_mod.evict_session("abc")
    assert "abc" not in messages_mod._sessions


def test_evict_session_unknown_id_is_noop():
    messages_mod.evict_session("does-not-exist")  # must not raise


def test_get_or_create_returns_same_object():
    s1 = messages_mod._get_or_create_session("xyz")
    s2 = messages_mod._get_or_create_session("xyz")
    assert s1 is s2


def test_access_promotes_to_most_recent():
    """Accessing an existing entry promotes it so it is not evicted next."""
    original_size = messages_mod._SESSION_CACHE_SIZE
    messages_mod._SESSION_CACHE_SIZE = 3
    try:
        messages_mod._get_or_create_session("old")
        messages_mod._get_or_create_session("middle")
        messages_mod._get_or_create_session("new")
        # Re-access "old" to promote it
        messages_mod._get_or_create_session("old")
        # Adding another entry should evict "middle" (now the LRU)
        messages_mod._get_or_create_session("newest")
        assert "old" in messages_mod._sessions
        assert "middle" not in messages_mod._sessions
    finally:
        messages_mod._SESSION_CACHE_SIZE = original_size
