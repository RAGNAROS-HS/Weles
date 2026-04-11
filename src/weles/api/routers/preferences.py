from fastapi import APIRouter, HTTPException

from weles.db.connection import get_db

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.delete("/{pref_id}", status_code=204)
async def delete_preference(pref_id: str) -> None:
    conn = get_db()
    cur = conn.execute("DELETE FROM preferences WHERE id = ?", (pref_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Preference not found")
