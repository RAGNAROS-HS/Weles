import json
from typing import Any

from weles.db.connection import get_db

_KNOWN_KEYS = {
    "follow_up_cadence",
    "proactive_surfacing",
    "decay_thresholds",
    "max_tool_calls_per_turn",
}


def get_all_settings() -> dict[str, Any]:
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: json.loads(row["value"]) for row in rows}


def get_setting(key: str) -> Any:
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return json.loads(row["value"])


def set_setting(key: str, value: Any) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value)),
    )
    conn.commit()


def known_keys() -> frozenset[str]:
    return frozenset(_KNOWN_KEYS)
