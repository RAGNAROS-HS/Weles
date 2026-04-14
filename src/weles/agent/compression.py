import os
from typing import Any

import anthropic
from anthropic.types import TextBlock

from weles.agent.session import CONTEXT_WINDOW, Session, estimated_tokens
from weles.db.connection import get_db

_PROTECTED_TAIL = 10  # last N messages are never compressed


def _compression_candidates(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the oldest 25% of messages, never touching the last _PROTECTED_TAIL."""
    eligible = messages[:-_PROTECTED_TAIL] if len(messages) > _PROTECTED_TAIL else []
    n = max(0, len(eligible) // 4)
    return eligible[:n]


def needs_compression(messages: list[dict[str, Any]]) -> bool:
    """Return True when estimated token count exceeds 80% of CONTEXT_WINDOW."""
    return estimated_tokens(messages) > int(0.8 * CONTEXT_WINDOW)


async def compress_tool_results(
    session_id: str,
    client: anthropic.Anthropic,
    turn_messages: list[dict[str, Any]],
) -> None:
    """Compress tool_result blocks in the given turn messages in-place (fire-and-forget).

    Replaces each tool_result content with a 2-sentence Claude summary.
    No DB write — tool results are ephemeral and not persisted.
    """
    model = os.environ.get("WELES_MODEL", "claude-sonnet-4-6")
    for msg in turn_messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        new_blocks: list[dict[str, Any]] = []
        changed = False
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                new_blocks.append(block)
                continue
            raw = block.get("content", "")
            if not raw:
                new_blocks.append(block)
                continue
            try:
                resp = client.messages.create(
                    model=model,
                    max_tokens=128,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Tool result:\n{raw}\n\n"
                                "Summarise what this tool result contributed "
                                "to the response in 2 sentences."
                            ),
                        }
                    ],
                )
                first = resp.content[0] if resp.content else None
                summary = first.text if isinstance(first, TextBlock) else str(raw)
                new_blocks.append({**block, "content": f"[Compressed] {summary}"})
                changed = True
            except Exception:
                new_blocks.append(block)
        if changed:
            msg["content"] = new_blocks
            msg["is_compressed"] = True


async def maybe_compress_context(
    session_id: str,
    client: anthropic.Anthropic,
    session: Session,
) -> None:
    """Summarise oldest user+assistant pairs when context exceeds 80% of CONTEXT_WINDOW.

    Compresses in-memory session messages and updates the DB.
    The last _PROTECTED_TAIL messages are never touched.
    """
    if not needs_compression(session.get_messages_for_context()):
        return

    candidates = _compression_candidates(session.messages)
    if not candidates:
        return

    model = os.environ.get("WELES_MODEL", "claude-sonnet-4-6")
    conn = get_db()

    i = 0
    while i < len(candidates) - 1:
        u = candidates[i]
        a = candidates[i + 1]
        if u.get("role") == "user" and a.get("role") == "assistant":
            u_text = u["content"] if isinstance(u["content"], str) else str(u["content"])
            a_text = a["content"] if isinstance(a["content"], str) else str(a["content"])
            try:
                resp = client.messages.create(
                    model=model,
                    max_tokens=256,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"User: {u_text}\nAssistant: {a_text}\n\n"
                                "Summarise this exchange in 2-3 sentences, "
                                "preserving recommendations, decisions, "
                                "and profile information revealed."
                            ),
                        }
                    ],
                )
                first = resp.content[0] if resp.content else None
                summary = first.text if isinstance(first, TextBlock) else f"{u_text} / {a_text}"
            except Exception:
                i += 2
                continue

            compressed = f"[Compressed] {summary}"
            u["content"] = compressed
            u["is_compressed"] = True
            a["content"] = compressed
            a["is_compressed"] = True
            conn.execute(
                "UPDATE messages SET content = ?, is_compressed = 1"
                " WHERE session_id = ? AND role = 'user' AND content = ?",
                (compressed, session_id, u_text),
            )
            conn.execute(
                "UPDATE messages SET content = ?, is_compressed = 1"
                " WHERE session_id = ? AND role = 'assistant' AND content = ?",
                (compressed, session_id, a_text),
            )
            i += 2
        else:
            i += 1
    conn.commit()
