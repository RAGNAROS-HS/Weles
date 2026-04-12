import uuid
from datetime import datetime
from typing import Any

from weles.db.connection import get_db


def get_history(domain: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    conn = get_db()
    query = "SELECT * FROM history"
    params: list[Any] = []
    filters = []
    if domain:
        filters.append("domain = ?")
        params.append(domain)
    if status:
        filters.append("status = ?")
        params.append(status)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def delete_history_item(item_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
    conn.commit()
    return cur.rowcount > 0


def add_to_history(
    item_name: str,
    category: str,
    domain: str,
    status: str,
    rating: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    conn = get_db()
    item_id = str(uuid.uuid4())
    now = datetime.utcnow()
    conn.execute(
        "INSERT INTO history (id, item_name, category, domain, status, rating, notes, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (item_id, item_name, category, domain, status, rating, notes, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM history WHERE id = ?", (item_id,)).fetchone()
    return dict(row)
