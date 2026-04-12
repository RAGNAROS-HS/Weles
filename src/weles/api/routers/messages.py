import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from weles.agent.client import get_client
from weles.agent.dispatch import ToolRegistry
from weles.agent.prompts import build_system_prompt
from weles.agent.stream import (
    AgentEvent,
    DoneEvent,
    TextDeltaEvent,
    ToolEndEvent,
    ToolErrorEvent,
    ToolStartEvent,
    stream_response,
)
from weles.db.connection import get_db
from weles.db.profile_repo import get_preferences, get_profile, set_first_session_at
from weles.utils.errors import ConfigurationError

router = APIRouter(tags=["messages"])


class MessageBody(BaseModel):
    content: str


def _get_session(session_id: str) -> dict[str, Any]:
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)


def _load_history(session_id: str) -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def _save_message(session_id: str, role: str, content: str, tool_name: str | None = None) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content, tool_name, is_compressed, created_at)"
        " VALUES (?, ?, ?, ?, ?, 0, ?)",
        (str(uuid.uuid4()), session_id, role, content, tool_name, datetime.utcnow()),
    )
    conn.commit()


def _set_session_title(session_id: str, content: str) -> None:
    conn = get_db()
    existing = conn.execute("SELECT title FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if existing and existing["title"] is None:
        title = content[:50]
        conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
        conn.commit()


def _is_first_message(session_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM messages WHERE session_id = ? AND role = 'user' LIMIT 1",
        (session_id,),
    ).fetchone()
    return row is None


@router.post("/sessions/{session_id}/messages")
async def post_message(session_id: str, body: MessageBody, request: Request) -> EventSourceResponse:
    _get_session(session_id)

    async def event_stream() -> AsyncIterator[dict[str, Any]]:
        is_first = _is_first_message(session_id)

        _save_message(session_id, "user", body.content)
        _set_session_title(session_id, body.content)

        if is_first:
            set_first_session_at(datetime.utcnow())
            request.app.state.is_first_run = False

        history = _load_history(session_id)
        session_row = _get_session(session_id)
        mode = session_row.get("mode", "general")
        try:
            system = build_system_prompt(mode, get_profile(), get_preferences())
        except ValueError as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
            return
        registry = ToolRegistry()

        try:
            client = get_client()
        except ConfigurationError as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
            return

        reply_parts: list[str] = []
        title = session_row.get("title") or body.content[:50]

        try:
            async for event in stream_response(
                client, history, registry.get_tool_schemas(), system
            ):
                sse = _agent_event_to_sse(event, title, session_id)
                if sse:
                    yield sse
                if isinstance(event, TextDeltaEvent):
                    reply_parts.append(event.text)
                elif isinstance(event, DoneEvent):
                    break
        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
            return

        if reply_parts:
            _save_message(session_id, "assistant", "".join(reply_parts))

    return EventSourceResponse(event_stream())


def _agent_event_to_sse(event: AgentEvent, title: str, session_id: str) -> dict[str, Any] | None:
    if isinstance(event, TextDeltaEvent):
        return {"event": "text_delta", "data": json.dumps({"delta": event.text})}
    if isinstance(event, ToolStartEvent):
        return {
            "event": "tool_start",
            "data": json.dumps({"tool": event.tool, "description": event.tool_use_id}),
        }
    if isinstance(event, ToolEndEvent):
        return {
            "event": "tool_end",
            "data": json.dumps({"tool": event.tool, "result_summary": event.result}),
        }
    if isinstance(event, ToolErrorEvent):
        return {
            "event": "tool_error",
            "data": json.dumps({"tool": event.tool, "error": event.error}),
        }
    if isinstance(event, DoneEvent):
        return {"event": "done", "data": json.dumps({"session_id": session_id, "title": title})}
    return None


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str) -> list[dict[str, Any]]:
    _get_session(session_id)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]
