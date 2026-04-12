import inspect
from collections.abc import Callable
from typing import Any, NamedTuple

from langsmith import traceable

from weles.utils.errors import MaxToolCallsError, ToolNotFoundError


class ToolResult(NamedTuple):
    summary: str
    data: Any


class ToolRegistry:
    def __init__(self, max_calls: int = 6) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._schemas: dict[str, dict[str, Any]] = {}
        self._max_calls = max_calls
        self._call_count = 0

    def register(self, name: str, handler: Callable[..., Any], schema: dict[str, Any]) -> None:
        self._handlers[name] = handler
        self._schemas[name] = schema

    def dispatch(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        if tool_name not in self._handlers:
            raise ToolNotFoundError(f"Unknown tool: {tool_name!r}")
        self._call_count += 1
        if self._call_count > self._max_calls:
            raise MaxToolCallsError(f"Research limit reached (max {self._max_calls})")
        result = self._handlers[tool_name](tool_input)
        if isinstance(result, ToolResult):
            return result
        s = str(result)
        return ToolResult(summary=s, data=s)

    @traceable(run_type="tool")
    async def adispatch(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        if tool_name not in self._handlers:
            raise ToolNotFoundError(f"Unknown tool: {tool_name!r}")
        self._call_count += 1
        if self._call_count > self._max_calls:
            raise MaxToolCallsError(f"Research limit reached (max {self._max_calls})")
        result = self._handlers[tool_name](tool_input)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, ToolResult):
            return result
        s = str(result)
        return ToolResult(summary=s, data=s)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [{"name": name, "input_schema": schema} for name, schema in self._schemas.items()]
