import uuid
from datetime import datetime, timedelta
from typing import Any

from weles.db.connection import get_db

_STATUS_PREFIX: dict[str, str] = {
    "bought": "Owned",
    "tried": "Tried",
    "recommended": "Recommended",
    "rated": "Rated",
    "skipped": "Skipped",
}


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
    from weles.db.settings_repo import get_setting

    now = datetime.utcnow()
    follow_up_due_at: datetime | None = None
    check_in_due_at: datetime | None = None

    if status == "recommended":
        cadence = get_setting("follow_up_cadence") or "off"
        if cadence == "weekly":
            follow_up_due_at = now + timedelta(days=7)
        elif cadence == "monthly":
            follow_up_due_at = now + timedelta(days=30)

    if status in ("bought", "tried"):
        if domain in ("fitness", "diet"):
            check_in_due_at = now + timedelta(days=30)
        elif domain in ("shopping", "lifestyle"):
            check_in_due_at = now + timedelta(days=90)

    conn = get_db()
    item_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO history"
        " (id, item_name, category, domain, status, rating, notes,"
        "  follow_up_due_at, check_in_due_at, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            item_id,
            item_name,
            category,
            domain,
            status,
            rating,
            notes,
            follow_up_due_at,
            check_in_due_at,
            now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM history WHERE id = ?", (item_id,)).fetchone()
    return dict(row)


def get_history_context(domain: str) -> str | None:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history WHERE domain = ? ORDER BY created_at DESC LIMIT 10",
        (domain,),
    ).fetchall()
    if not rows:
        return None

    lines: list[str] = []
    for row in rows:
        r = dict(row)
        prefix = _STATUS_PREFIX.get(r["status"], r["status"].capitalize())
        parts = [r["category"], r["status"]]
        if r.get("rating") is not None:
            parts.append(f"rated {r['rating']}/5")
        if r.get("notes"):
            parts.append(f"notes: {r['notes']}")
        lines.append(f"{prefix}: {r['item_name']} ({', '.join(parts)}).")

    domain_label = domain.capitalize()
    return f"[History — {domain_label}]\n" + "\n".join(lines)
