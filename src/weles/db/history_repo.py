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


def get_history(
    domain: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    conn = get_db()
    base = "FROM history"
    params: list[Any] = []
    filters = []
    if domain:
        filters.append("domain = ?")
        params.append(domain)
    if status:
        filters.append("status = ?")
        params.append(status)
    where = (" WHERE " + " AND ".join(filters)) if filters else ""
    total: int = conn.execute(f"SELECT COUNT(*) {base}{where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * {base}{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


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


def snooze_check_in(item_id: str, days: int = 30) -> bool:
    """Defer a bought/tried item's check_in_due_at by `days` from now.

    Returns True if the row was found and updated, False otherwise.
    """
    now = datetime.utcnow()
    new_due = now + timedelta(days=days)
    conn = get_db()
    cur = conn.execute(
        "UPDATE history SET check_in_due_at = ? WHERE id = ? AND status IN ('bought', 'tried')",
        (new_due, item_id),
    )
    conn.commit()
    return cur.rowcount > 0


def snooze_follow_up(item_id: str, cadence_days: int) -> bool:
    """Defer a recommended item's follow_up_due_at by cadence_days from now.

    Returns True if the row was found and updated, False otherwise.
    """
    now = datetime.utcnow()
    new_due = now + timedelta(days=cadence_days)
    conn = get_db()
    cur = conn.execute(
        "UPDATE history SET follow_up_due_at = ? WHERE id = ? AND status = 'recommended'",
        (new_due, item_id),
    )
    conn.commit()
    return cur.rowcount > 0


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
    return (
        f"[History — {domain_label}]\n"
        '<untrusted_data source="user_history">\n' + "\n".join(lines) + "\n</untrusted_data>"
    )
