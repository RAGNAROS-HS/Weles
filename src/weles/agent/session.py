from typing import Any


class Session:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.asked_this_session: set[str] = set()

    def add_message(self, role: str, content: str | list[Any]) -> None:
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> list[dict[str, Any]]:
        return self.messages
