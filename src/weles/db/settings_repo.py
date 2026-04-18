import json
import logging
from typing import Any

from weles.db.connection import get_db

logger = logging.getLogger(__name__)

_KNOWN_KEYS = {
    "follow_up_cadence",
    "proactive_surfacing",
    "decay_thresholds",
    "max_tool_calls_per_turn",
}

# Validators for user-configurable keys only. Internal cache keys (e.g. qc_cache_*)
# bypass these checks and are written directly via set_setting.
_SETTING_VALIDATORS: dict[str, Any] = {
    "max_tool_calls_per_turn": lambda v: (
        isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 20
    ),
    "follow_up_cadence": lambda v: v in {"weekly", "monthly", "off"},
    # stored and compared as string "true"/"false" by existing code
    "proactive_surfacing": lambda v: isinstance(v, bool) or v in {"true", "false"},
    "decay_thresholds": lambda v: isinstance(v, dict),
}

_SETTING_DESCRIPTIONS = {
    "max_tool_calls_per_turn": "integer between 1 and 20",
    "follow_up_cadence": "'weekly', 'monthly', or 'off'",
    "proactive_surfacing": "boolean or 'true'/'false'",
    "decay_thresholds": "dict",
}


def get_all_settings() -> dict[str, Any]:
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            logger.warning("Skipping corrupt settings row key=%r", row["key"])
    return result


def get_setting(key: str) -> Any:
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        logger.warning("Corrupt settings value for key=%r; returning None", key)
        return None


def set_setting(key: str, value: Any) -> None:
    """Write a setting. Validates value type for user-configurable keys.

    Raises ValueError if key is a known user setting with an invalid value.
    Unknown keys (e.g. internal qc_cache_* entries) are written without validation.
    """
    if key in _KNOWN_KEYS:
        validator = _SETTING_VALIDATORS[key]
        if not validator(value):
            description = _SETTING_DESCRIPTIONS[key]
            raise ValueError(f"Invalid value for {key!r}: expected {description}, got {value!r}")
    conn = get_db()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value)),
    )
    conn.commit()


def known_keys() -> frozenset[str]:
    return frozenset(_KNOWN_KEYS)
