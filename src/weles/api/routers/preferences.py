from typing import Any

from fastapi import APIRouter, HTTPException

from weles.db.connection import get_db

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("")
async def list_preferences() -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM preferences ORDER BY created_at ASC").fetchall()
    return [dict(row) for row in rows]


@router.delete("/{pref_id}", status_code=204)
async def delete_preference(pref_id: str) -> None:
    conn = get_db()
    cur = conn.execute("DELETE FROM preferences WHERE id = ?", (pref_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Preference not found")
