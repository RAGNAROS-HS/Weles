import os
import sqlite3
import threading
from pathlib import Path

_local = threading.local()


def get_db() -> sqlite3.Connection:
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    if conn is None:
        raw = os.getenv("WELES_DB_PATH", str(Path.home() / ".weles" / "weles.db"))
        db_file = Path(raw).expanduser()
        db_file.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_file), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn
