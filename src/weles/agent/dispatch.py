from collections.abc import Callable
from typing import Any

from weles.utils.errors import ToolNotFoundError


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

    def register(self, name: str, handler: Callable[..., Any], schema: dict[str, Any]) -> None:
        self._handlers[name] = handler
        self._schemas[name] = schema

    def dispatch(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        if tool_name not in self._handlers:
            raise ToolNotFoundError(f"Unknown tool: {tool_name!r}")
        result = self._handlers[tool_name](tool_input)
        return str(result)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "input_schema": schema}
            for name, schema in self._schemas.items()
        ]
