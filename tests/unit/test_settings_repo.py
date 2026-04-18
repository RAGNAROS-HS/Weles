import pytest

from weles.db.settings_repo import get_all_settings, get_setting, set_setting


def test_get_all_settings_skips_corrupt_row(tmp_db: object) -> None:
    from weles.db.connection import get_db

    conn = get_db()
    conn.execute("INSERT INTO settings (key, value) VALUES ('corrupt_key', 'not-json{{')")
    conn.commit()

    result = get_all_settings()
    assert "corrupt_key" not in result
    assert "max_tool_calls_per_turn" in result


def test_get_setting_returns_none_on_corrupt_row(tmp_db: object) -> None:
    from weles.db.connection import get_db

    conn = get_db()
    conn.execute("INSERT INTO settings (key, value) VALUES ('corrupt_key', 'bad}')")
    conn.commit()

    assert get_setting("corrupt_key") is None


def test_set_setting_max_tool_calls_valid(tmp_db: object) -> None:
    set_setting("max_tool_calls_per_turn", 6)
    assert get_setting("max_tool_calls_per_turn") == 6


def test_set_setting_max_tool_calls_string_raises(tmp_db: object) -> None:
    with pytest.raises(ValueError, match="max_tool_calls_per_turn"):
        set_setting("max_tool_calls_per_turn", "abc")


def test_set_setting_max_tool_calls_zero_raises(tmp_db: object) -> None:
    with pytest.raises(ValueError, match="max_tool_calls_per_turn"):
        set_setting("max_tool_calls_per_turn", 0)


def test_set_setting_max_tool_calls_too_large_raises(tmp_db: object) -> None:
    with pytest.raises(ValueError, match="max_tool_calls_per_turn"):
        set_setting("max_tool_calls_per_turn", 21)


def test_set_setting_max_tool_calls_bool_raises(tmp_db: object) -> None:
    # bool is a subclass of int in Python; the validator must reject it explicitly
    with pytest.raises(ValueError, match="max_tool_calls_per_turn"):
        set_setting("max_tool_calls_per_turn", True)


def test_set_setting_follow_up_cadence_valid(tmp_db: object) -> None:
    for val in ("weekly", "monthly", "off"):
        set_setting("follow_up_cadence", val)
        assert get_setting("follow_up_cadence") == val


def test_set_setting_follow_up_cadence_invalid_raises(tmp_db: object) -> None:
    with pytest.raises(ValueError, match="follow_up_cadence"):
        set_setting("follow_up_cadence", "daily")


def test_set_setting_proactive_surfacing_bool_valid(tmp_db: object) -> None:
    set_setting("proactive_surfacing", True)
    assert get_setting("proactive_surfacing") is True


def test_set_setting_proactive_surfacing_string_valid(tmp_db: object) -> None:
    # existing code stores and reads proactive_surfacing as "true"/"false" strings
    set_setting("proactive_surfacing", "false")
    assert get_setting("proactive_surfacing") == "false"


def test_set_setting_proactive_surfacing_invalid_raises(tmp_db: object) -> None:
    with pytest.raises(ValueError, match="proactive_surfacing"):
        set_setting("proactive_surfacing", "yes")


def test_set_setting_unknown_key_passes_through(tmp_db: object) -> None:
    # Internal cache entries (e.g. qc_cache_*) bypass validation
    set_setting("qc_cache_abc123", {"timestamp": "2026-01-01", "found": False})
    result = get_setting("qc_cache_abc123")
    assert result == {"timestamp": "2026-01-01", "found": False}
