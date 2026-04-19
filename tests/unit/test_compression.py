"""Tests for context compression — specifically that updates target rows by ID."""

import contextlib
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import anthropic
import pytest

from weles.agent.compression import maybe_compress_context
from weles.agent.session import Session


def _insert_messages(conn: object, session_id: str, pairs: list[tuple[str, str]]) -> list[str]:
    """Insert user+assistant message pairs, return list of inserted IDs (in order)."""
    ids: list[str] = []
    now = datetime.utcnow()
    for i, (user_content, assistant_content) in enumerate(pairs):
        uid = str(uuid.uuid4())
        aid = str(uuid.uuid4())
        offset = timedelta(seconds=i * 2)
        conn.execute(  # type: ignore[union-attr]
            "INSERT INTO messages"
            " (id, session_id, role, content, tool_name, is_compressed, created_at)"
            " VALUES (?, ?, 'user', ?, NULL, 0, ?)",
            (uid, session_id, user_content, now + offset),
        )
        conn.execute(  # type: ignore[union-attr]
            "INSERT INTO messages"
            " (id, session_id, role, content, tool_name, is_compressed, created_at)"
            " VALUES (?, ?, 'assistant', ?, NULL, 0, ?)",
            (aid, session_id, assistant_content, now + offset + timedelta(seconds=1)),
        )
        ids.extend([uid, aid])
    conn.commit()  # type: ignore[union-attr]
    return ids


def _make_session_from_db(session_id: str) -> Session:
    """Load messages from DB into a Session (mirrors _load_history behaviour)."""
    from weles.db.connection import get_db

    conn = get_db()
    rows = conn.execute(
        "SELECT id, role, content, is_compressed FROM messages"
        " WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    session = Session(session_id)
    session.messages = [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "is_compressed": bool(row["is_compressed"]),
        }
        for row in rows
    ]
    return session


@pytest.mark.asyncio
async def test_compression_uses_id_not_content(tmp_db: object) -> None:
    """When two user messages have identical text, only the first is compressed."""
    from weles.db.connection import get_db

    conn = get_db()

    # Create a session
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, title, mode, created_at) VALUES (?, NULL, 'general', ?)",
        (session_id, datetime.utcnow()),
    )
    conn.commit()

    # Insert 10 pairs so oldest pair is a compression candidate.
    # Pairs 0 and 2 both have user content "ok" — this is the duplicate-content trap.
    pairs = [
        ("ok", "sure"),  # pair 0 — oldest, will be compressed
        ("what about X?", "X is good"),  # pair 1
        ("ok", "noted"),  # pair 2 — same user text, should NOT be compressed
        ("another thing", "alright"),  # pair 3
        ("more", "yes"),  # pair 4
        ("test", "response"),  # pair 5
        ("query", "answer"),  # pair 6
        ("question", "answer2"),  # pair 7
        ("ask", "reply"),  # pair 8
        ("final", "done"),  # pair 9 — recent, protected tail
    ]
    ids = _insert_messages(conn, session_id, pairs)
    # ids[0] = pair0 user "ok" (will be compressed)
    # ids[1] = pair0 assistant "sure"
    # ids[4] = pair2 user "ok" (must NOT be compressed)

    session = _make_session_from_db(session_id)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Summary of the exchange.")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    # Force compression to fire regardless of token count
    from unittest.mock import patch

    with patch("weles.agent.compression.needs_compression", return_value=True):
        await maybe_compress_context(session_id, mock_client, session)

    # pair0 user "ok" should be compressed
    pair0_user = conn.execute(
        "SELECT content, is_compressed FROM messages WHERE id = ?", (ids[0],)
    ).fetchone()
    assert pair0_user["is_compressed"] == 1
    assert pair0_user["content"].startswith("[Compressed]")

    # pair2 user "ok" must remain unchanged — old bug would have overwritten this too
    pair2_user = conn.execute(
        "SELECT content, is_compressed FROM messages WHERE id = ?", (ids[4],)
    ).fetchone()
    assert pair2_user["is_compressed"] == 0
    assert pair2_user["content"] == "ok"


@pytest.mark.asyncio
async def test_compression_continues_on_api_timeout(tmp_db: object) -> None:
    """Compression task continues and logs ERROR when APITimeoutError is raised."""
    from unittest.mock import patch

    from weles.db.connection import get_db

    conn = get_db()
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, title, mode, created_at) VALUES (?, NULL, 'general', ?)",
        (session_id, datetime.utcnow()),
    )
    conn.commit()

    pairs = [("question", "answer")] * 10
    ids = _insert_messages(conn, session_id, pairs)

    session = _make_session_from_db(session_id)

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())

    with (
        patch("weles.agent.compression.needs_compression", return_value=True),
        patch("weles.agent.compression.logger") as mock_logger,
    ):
        await maybe_compress_context(session_id, mock_client, session)

    mock_logger.error.assert_called()
    call_args = mock_logger.error.call_args_list
    assert any("timed out" in str(args[0]) for args, _ in call_args)
    first_msg = conn.execute(
        "SELECT is_compressed FROM messages WHERE id = ?", (ids[0],)
    ).fetchone()
    assert first_msg["is_compressed"] == 0


@pytest.mark.asyncio
async def test_db_failure_leaves_in_memory_state_unchanged(tmp_db: object) -> None:
    """If a DB execute raises after first update, in-memory messages must be unchanged."""
    from unittest.mock import patch

    from weles.db.connection import get_db

    conn = get_db()
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, title, mode, created_at) VALUES (?, NULL, 'general', ?)",
        (session_id, datetime.utcnow()),
    )
    conn.commit()

    pairs = [("question", "answer")] * 10
    _insert_messages(conn, session_id, pairs)
    session = _make_session_from_db(session_id)

    original_contents = [m["content"] for m in session.messages]
    original_compressed = [m["is_compressed"] for m in session.messages]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Summary.")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    call_count = 0

    def execute_side_effect(sql: str, params: tuple = ()) -> object:  # type: ignore[misc]
        nonlocal call_count
        if "UPDATE messages" in sql:
            call_count += 1
            if call_count >= 2:
                raise RuntimeError("DB error")
        return conn.execute(sql, params)

    with (
        patch("weles.agent.compression.needs_compression", return_value=True),
        patch("weles.agent.compression.get_db") as mock_get_db,
    ):
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = execute_side_effect
        mock_get_db.return_value = mock_conn

        with contextlib.suppress(RuntimeError):
            await maybe_compress_context(session_id, mock_client, session)

    # In-memory state must be unchanged since commit never happened
    assert [m["content"] for m in session.messages] == original_contents
    assert [m["is_compressed"] for m in session.messages] == original_compressed
