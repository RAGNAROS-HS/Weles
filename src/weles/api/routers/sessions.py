import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from weles.api.routers.messages import evict_session
from weles.api.session_start import run_session_start_checks
from weles.db.connection import get_db

router = APIRouter(prefix="/sessions", tags=["sessions"])

_VALID_MODES = {"general", "shopping", "diet", "fitness", "lifestyle"}


class SessionPatch(BaseModel):
    title: str | None = None
    mode: str | None = None


def _session_row(session_id: str) -> dict[str, Any] | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def _session_preview(session_id: str) -> str | None:
    conn = get_db()
    row = conn.execute(
        "SELECT content FROM messages WHERE session_id = ? AND role = 'user'"
        " ORDER BY created_at ASC LIMIT 1",
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    return str(row["content"])[:60]


@router.post("", status_code=201)
async def create_session() -> dict[str, Any]:
    conn = get_db()
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    conn.execute(
        "INSERT INTO sessions (id, title, mode, created_at) VALUES (?, NULL, 'general', ?)",
        (session_id, now),
    )
    conn.commit()
    checks = await run_session_start_checks(conn)
    return {
        "id": session_id,
        "title": None,
        "mode": "general",
        "created_at": now.isoformat(),
        "session_start_prompt": checks.to_dict(),
    }


@router.get("")
async def list_sessions(search: str | None = None) -> list[dict[str, Any]]:
    conn = get_db()
    if search:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE title IS NOT NULL AND LOWER(title) LIKE LOWER(?)"
            " ORDER BY created_at DESC",
            (f"%{search}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["preview"] = _session_preview(d["id"])
        result.append(d)
    return result


@router.patch("/{session_id}")
async def patch_session(session_id: str, body: SessionPatch) -> dict[str, Any]:
    row = _session_row(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.mode is not None and body.mode not in _VALID_MODES:
        raise HTTPException(status_code=422, detail=f"Invalid mode: {body.mode!r}")

    conn = get_db()
    if body.title is not None:
        conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (body.title, session_id))
    if body.mode is not None:
        conn.execute("UPDATE sessions SET mode = ? WHERE id = ?", (body.mode, session_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone())


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str) -> None:
    row = _session_row(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    evict_session(session_id)
