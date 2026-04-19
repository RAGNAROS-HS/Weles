import asyncio
import logging
import os
from typing import Any

import anthropic
from anthropic.types import TextBlock

from weles.agent.session import CONTEXT_WINDOW, Session, estimated_tokens
from weles.db.connection import get_db

logger = logging.getLogger(__name__)

_PROTECTED_TAIL = 10  # last N messages are never compressed


def _compression_candidates(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the oldest 25% of messages, never touching the last _PROTECTED_TAIL."""
    eligible = messages[:-_PROTECTED_TAIL] if len(messages) > _PROTECTED_TAIL else []
    n = max(0, len(eligible) // 4)
    return eligible[:n]


def needs_compression(messages: list[dict[str, Any]]) -> bool:
    """Return True when estimated token count exceeds 80% of CONTEXT_WINDOW."""
    return estimated_tokens(messages) > int(0.8 * CONTEXT_WINDOW)


async def maybe_compress_context(
    session_id: str,
    client: anthropic.Anthropic,
    session: Session,
) -> None:
    """Summarise oldest user+assistant pairs when context exceeds 80% of CONTEXT_WINDOW.

    Compresses in-memory session messages and updates the DB.
    The last _PROTECTED_TAIL messages are never touched.
    Sync Claude API calls run in a thread pool executor to avoid blocking the event loop.
    """
    if not needs_compression(session.get_messages_for_context()):
        return

    candidates = _compression_candidates(session.messages)
    if not candidates:
        return

    model = os.environ.get("WELES_MODEL", "claude-sonnet-4-6")
    loop = asyncio.get_event_loop()
    conn = get_db()

    # Phase 1: summarise all pairs, collecting (msg_dict, compressed_text) without mutating yet
    updates: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    i = 0
    while i < len(candidates) - 1:
        u = candidates[i]
        a = candidates[i + 1]
        if u.get("role") == "user" and a.get("role") == "assistant":
            u_text = u["content"] if isinstance(u["content"], str) else str(u["content"])
            a_text = a["content"] if isinstance(a["content"], str) else str(a["content"])
            prompt = (
                f"User: {u_text}\nAssistant: {a_text}\n\n"
                "Summarise this exchange in 2-3 sentences, "
                "preserving recommendations, decisions, "
                "and profile information revealed."
            )

            def _call(p: str = prompt) -> anthropic.types.Message:
                return client.messages.create(
                    model=model,
                    max_tokens=256,
                    messages=[{"role": "user", "content": p}],
                    timeout=30.0,
                )

            try:
                resp = await loop.run_in_executor(None, _call)
                first = resp.content[0] if resp.content else None
                summary = first.text if isinstance(first, TextBlock) else f"{u_text} / {a_text}"
            except anthropic.APITimeoutError:
                logger.error("Compression timed out for session %s", session_id, exc_info=True)
                i += 2
                continue
            except Exception:
                logger.error("Compression failed for session %s", session_id, exc_info=True)
                i += 2
                continue

            updates.append((u, a, f"[Compressed] {summary}"))
            i += 2
        else:
            i += 1

    if not updates:
        return

    # Phase 2: write to DB and commit — in-memory state is untouched until after commit
    for u, a, compressed in updates:
        conn.execute(
            "UPDATE messages SET content = ?, is_compressed = 1 WHERE id = ?",
            (compressed, u["id"]),
        )
        conn.execute(
            "UPDATE messages SET content = ?, is_compressed = 1 WHERE id = ?",
            (compressed, a["id"]),
        )
    conn.commit()

    # Phase 3: update in-memory state only after successful commit
    for u, a, compressed in updates:
        u["content"] = compressed
        u["is_compressed"] = True
        a["content"] = compressed
        a["is_compressed"] = True
