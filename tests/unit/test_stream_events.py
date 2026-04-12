import json
from unittest.mock import MagicMock

import pytest
from anthropic.types import RawMessageStopEvent, ToolUseBlock

from weles.agent.dispatch import ToolRegistry
from weles.agent.stream import (
    DoneEvent,
    ToolErrorEvent,
    ToolStartEvent,
    stream_response,
)
from weles.api.routers.messages import _agent_event_to_sse


def test_tool_start_event_serialises_to_tool_start_sse():
    description = "Searching r/BuyItForLife for 'knife'…"
    event = ToolStartEvent(tool="search_reddit", description=description)
    sse = _agent_event_to_sse(event, "title", "session-id")
    assert sse is not None
    assert sse["event"] == "tool_start"
    payload = json.loads(sse["data"])
    assert payload["tool"] == "search_reddit"
    assert payload["description"] == "Searching r/BuyItForLife for 'knife'…"


def test_tool_error_event_serialises_to_tool_error_sse():
    event = ToolErrorEvent(tool="search_reddit", error="Request timed out")
    sse = _agent_event_to_sse(event, "title", "session-id")
    assert sse is not None
    assert sse["event"] == "tool_error"
    payload = json.loads(sse["data"])
    assert payload["tool"] == "search_reddit"
    assert payload["error"] == "Request timed out"


@pytest.mark.asyncio
async def test_tool_dispatch_exception_emits_tool_error_does_not_reraise():
    """When a registered handler raises, ToolErrorEvent is emitted; stream does not abort."""

    def bad_handler(_: dict) -> str:
        raise ValueError("boom")

    # First Claude response: stop_reason=tool_use with one tool use block
    first_stream = MagicMock()
    first_stream.__enter__ = MagicMock(return_value=first_stream)
    first_stream.__exit__ = MagicMock(return_value=False)
    first_stream.__iter__ = MagicMock(return_value=iter([]))
    first_message = MagicMock()
    first_message.stop_reason = "tool_use"
    first_message.content = [
        ToolUseBlock(id="tu_1", name="bad_tool", input={"x": 1}, type="tool_use")
    ]
    first_stream.get_final_message = MagicMock(return_value=first_message)

    # Second Claude response: stop_reason=end_turn, no tool calls
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

    registry = ToolRegistry()
    registry.register("bad_tool", bad_handler, {"type": "object", "properties": {}})

    events = []
    async for event in stream_response(mock_client, [], [], [], registry):
        events.append(event)

    error_events = [e for e in events if isinstance(e, ToolErrorEvent)]
    assert len(error_events) == 1
    assert error_events[0].tool == "bad_tool"
    assert "boom" in error_events[0].error
    assert isinstance(events[-1], DoneEvent)
