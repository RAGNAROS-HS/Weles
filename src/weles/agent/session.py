import json
from typing import Any

CONTEXT_WINDOW = 200_000


def estimated_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate token count for a list of messages using word count * 1.3."""
    if not messages:
        return 0
    parts: list[str] = []
    for m in messages:
        c = m.get("content", "")
        parts.append(c if isinstance(c, str) else json.dumps(c))
    return int(len(" ".join(parts).split()) * 1.3)


class Session:
    def __init__(self, session_id: str = "") -> None:
        self.session_id = session_id
        self.messages: list[dict[str, Any]] = []
        self.asked_this_session: set[str] = set()

    def add_message(self, role: str, content: str | list[Any], is_compressed: bool = False) -> None:
        self.messages.append({"role": role, "content": content, "is_compressed": is_compressed})

    def get_messages(self) -> list[dict[str, Any]]:
        return self.messages

    def get_messages_for_context(self) -> list[dict[str, Any]]:
        """Return messages as role/content dicts for the Claude API.

        Strips internal tracking fields; compressed messages are returned with their
        already-substituted summary content (stored in the content field).
        """
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]
