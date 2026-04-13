import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from weles.agent.client import get_client
from weles.agent.context import check_missing_fields
from weles.agent.dispatch import ToolRegistry
from weles.agent.prompts import build_system_prompt
from weles.agent.session import Session
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
from weles.db.history_repo import get_history_context
from weles.db.profile_repo import get_preferences, get_profile, set_first_session_at
from weles.db.settings_repo import get_setting
from weles.research.routing import get_subcategories, get_subreddits
from weles.tools.history_tools import ADD_TO_HISTORY_SCHEMA, add_to_history_handler
from weles.tools.profile_tools import SAVE_PROFILE_FIELD_SCHEMA, save_profile_field_handler
from weles.tools.reddit import SEARCH_REDDIT_SCHEMA, search_reddit_handler
from weles.utils.errors import ConfigurationError


def make_search_reddit_handler(
    mode: str,
) -> "Callable[[dict[str, Any]], Awaitable[object]]":
    """Return a search_reddit handler that resolves subcategory → subreddits for the given mode."""

    async def handler(tool_input: dict[str, Any]) -> object:
        if not tool_input.get("subreddits"):
            subcategory = tool_input.get("subcategory") or None
            tool_input = {**tool_input, "subreddits": get_subreddits(mode, subcategory)}
        return await search_reddit_handler(tool_input)

    return handler


_MODE_TO_DOMAIN = {
    "shopping": "shopping",
    "diet": "diet",
    "fitness": "fitness",
    "lifestyle": "lifestyle",
}

router = APIRouter(tags=["messages"])

# In-memory per-session state (survives requests, reset on server restart)
_sessions: dict[str, Session] = {}


def _get_or_create_session(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session()
    return _sessions[session_id]


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
        profile = get_profile()
        try:
            system = build_system_prompt(mode, profile, get_preferences())
        except ValueError as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
            return

        if mode != "general":
            subcategories = get_subcategories(mode)
            if subcategories:
                cats = ", ".join(subcategories)
                system = system + [
                    {
                        "type": "text",
                        "text": f"Available search subcategories for {mode} mode: {cats}.",
                    }
                ]

        # Inject missing-field note into the user turn
        mem_session = _get_or_create_session(session_id)
        missing = check_missing_fields(mode, profile)
        unasked = [f for f in missing if f not in mem_session.asked_this_session]
        if unasked:
            note = (
                f"[System: Profile fields unset and relevant: {unasked}. "
                "Infer from user message if possible and call save_profile_field. "
                "Otherwise ask for at most one.]"
            )
            history[-1]["content"] = history[-1]["content"] + "\n\n" + note
            mem_session.asked_this_session.update(unasked)

        # Inject history context for mode-specific domains
        history_domain = _MODE_TO_DOMAIN.get(mode)
        if history_domain:
            history_ctx = get_history_context(history_domain)
            if history_ctx:
                history[-1]["content"] = history[-1]["content"] + "\n\n" + history_ctx

        max_calls = int(get_setting("max_tool_calls_per_turn") or 6)
        registry = ToolRegistry(max_calls=max_calls)
        registry.register(
            "save_profile_field",
            save_profile_field_handler,
            SAVE_PROFILE_FIELD_SCHEMA,
        )
        registry.register(
            "add_to_history",
            add_to_history_handler,
            ADD_TO_HISTORY_SCHEMA,
        )
        registry.register(
            "search_reddit",
            make_search_reddit_handler(mode),
            SEARCH_REDDIT_SCHEMA,
        )

        try:
            client = get_client()
        except ConfigurationError as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
            return

        reply_parts: list[str] = []
        title = session_row.get("title") or body.content[:50]

        try:
            async for event in stream_response(
                client, history, registry.get_tool_schemas(), system, registry
            ):
                sse = _agent_event_to_sse(event, title, session_id)
                if sse:
                    yield sse
                if isinstance(event, TextDeltaEvent):
                    reply_parts.append(event.text)
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
            "data": json.dumps({"tool": event.tool, "description": event.description}),
        }
    if isinstance(event, ToolEndEvent):
        return {
            "event": "tool_end",
            "data": json.dumps({"tool": event.tool, "result_summary": event.result_summary}),
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
