import os
import sqlite3
import threading
from pathlib import Path

_local = threading.local()


def get_db() -> sqlite3.Connection:
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    if conn is None:
        db_path = os.getenv("WELES_DB_PATH", str(Path.home() / ".weles" / "weles.db"))
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn
