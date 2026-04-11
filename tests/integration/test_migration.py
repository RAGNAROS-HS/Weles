import json
import sqlite3
from pathlib import Path


def test_migration_applies_cleanly(tmp_db: Path) -> None:
    assert tmp_db.exists()


def test_all_tables_exist(tmp_db: Path) -> None:
    conn = sqlite3.connect(tmp_db)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic%'"
        ).fetchall()
    }
    conn.close()
    assert tables == {"sessions", "messages", "profile", "history", "preferences", "settings"}


def test_default_settings_present(tmp_db: Path) -> None:
    conn = sqlite3.connect(tmp_db)
    rows = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM settings").fetchall()}
    conn.close()

    assert rows["follow_up_cadence"] == '"off"'
    assert rows["proactive_surfacing"] == '"true"'
    assert rows["max_tool_calls_per_turn"] == '"6"'

    thresholds = json.loads(rows["decay_thresholds"])
    assert thresholds["goals"] == 60
    assert thresholds["fitness_level"] == 90
    assert thresholds["dietary_approach"] == 90
    assert thresholds["body_metrics"] == 180
    assert thresholds["taste_lifestyle"] == 365


def test_alembic_revision(tmp_db: Path) -> None:
    conn = sqlite3.connect(tmp_db)
    revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    conn.close()
    assert revision == "001_initial"
