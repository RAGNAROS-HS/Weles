from unittest.mock import MagicMock

import pytest
from anthropic.types import RawMessageStopEvent, ToolUseBlock

from weles.agent.dispatch import ToolRegistry
from weles.agent.stream import ToolErrorEvent, stream_response
from weles.utils.errors import MaxToolCallsError


def test_7th_dispatch_raises_max_tool_calls_error() -> None:
    registry = ToolRegistry(max_calls=6)
    registry.register("t", lambda _: "ok", {"type": "object", "properties": {}})

    for _ in range(6):
        registry.dispatch("t", {})

    with pytest.raises(MaxToolCallsError):
        registry.dispatch("t", {})


def test_call_count_resets_between_sessions() -> None:
    """Each ToolRegistry instance has its own counter; sessions don't share state."""
    r1 = ToolRegistry(max_calls=1)
    r1.register("t", lambda _: "ok", {"type": "object"})
    r1.dispatch("t", {})  # count = 1, no error

    r2 = ToolRegistry(max_calls=1)
    r2.register("t", lambda _: "ok", {"type": "object"})
    r2.dispatch("t", {})  # fresh count = 1, should not raise


@pytest.mark.asyncio
async def test_exceeding_limit_emits_max_tool_calls_event_with_correct_fields() -> None:
    """When tool call limit is exceeded, ToolErrorEvent has tool='max_tool_calls'
    and error='Research limit reached'."""

    # First Claude response: 2 tool_use blocks; max_calls=1 so second raises
    first_stream = MagicMock()
    first_stream.__enter__ = MagicMock(return_value=first_stream)
    first_stream.__exit__ = MagicMock(return_value=False)
    first_stream.__iter__ = MagicMock(return_value=iter([]))
    first_message = MagicMock()
    first_message.stop_reason = "tool_use"
    first_message.content = [
        ToolUseBlock(id="tu_1", name="search_reddit", input={"query": "a"}, type="tool_use"),
        ToolUseBlock(id="tu_2", name="search_reddit", input={"query": "b"}, type="tool_use"),
    ]
    first_stream.get_final_message = MagicMock(return_value=first_message)

    second_stream = MagicMock()
    second_stream.__enter__ = MagicMock(return_value=second_stream)
    second_stream.__exit__ = MagicMock(return_value=False)
    second_stream.__iter__ = MagicMock(
        return_value=iter([RawMessageStopEvent(type="message_stop")])
    )
    second_message = MagicMock()
    second_message.stop_reason = "end_turn"
    second_message.content = []
    second_stream.get_final_message = MagicMock(return_value=second_message)

    mock_client = MagicMock()
    mock_client.messages.stream.side_effect = [first_stream, second_stream]

    from weles.agent.dispatch import ToolResult

    async def mock_handler(_: dict) -> ToolResult:
        return ToolResult(summary="ok", data=[])

    registry = ToolRegistry(max_calls=1)
    registry.register("search_reddit", mock_handler, {"type": "object"})

    events = []
    async for event in stream_response(mock_client, [], [], [], registry):
        events.append(event)

    error_events = [e for e in events if isinstance(e, ToolErrorEvent)]
    max_calls_errors = [e for e in error_events if e.tool == "max_tool_calls"]
    assert len(max_calls_errors) >= 1
    assert max_calls_errors[0].error == "Research limit reached"
