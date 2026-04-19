import inspect
import logging
from collections.abc import Callable
from typing import Any, NamedTuple

from langsmith import traceable

from weles.utils.errors import MaxToolCallsError, ToolNotFoundError

log = logging.getLogger(__name__)


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

    def _truncate_inputs(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        schema = self._schemas.get(tool_name, {})
        props = schema.get("properties", {})
        result = dict(tool_input)
        for field, spec in props.items():
            max_len = spec.get("maxLength")
            val = result.get(field)
            if max_len and isinstance(val, str) and len(val) > max_len:
                log.warning("tool=%s field=%s truncated %d→%d", tool_name, field, len(val), max_len)
                result[field] = val[:max_len]
        return result

    def dispatch(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        if tool_name not in self._handlers:
            raise ToolNotFoundError(f"Unknown tool: {tool_name!r}")
        if self._call_count >= self._max_calls:
            raise MaxToolCallsError(f"Research limit reached (max {self._max_calls})")
        self._call_count += 1
        tool_input = self._truncate_inputs(tool_name, tool_input)
        result = self._handlers[tool_name](tool_input)
        if isinstance(result, ToolResult):
            return result
        s = str(result)
        return ToolResult(summary=s, data=s)

    @traceable(run_type="tool")
    async def adispatch(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        if tool_name not in self._handlers:
            raise ToolNotFoundError(f"Unknown tool: {tool_name!r}")
        if self._call_count >= self._max_calls:
            raise MaxToolCallsError(f"Research limit reached (max {self._max_calls})")
        self._call_count += 1
        tool_input = self._truncate_inputs(tool_name, tool_input)
        result = self._handlers[tool_name](tool_input)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, ToolResult):
            return result
        s = str(result)
        return ToolResult(summary=s, data=s)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [{"name": name, "input_schema": schema} for name, schema in self._schemas.items()]
