"""Integration tests: tool_end SSE payload includes field and value for profile tools."""

import json
from unittest.mock import MagicMock

import pytest
from anthropic.types import RawContentBlockDeltaEvent, RawMessageStopEvent, TextDelta, ToolUseBlock

from weles.agent.stream import ToolEndEvent
from weles.api.routers.messages import _agent_event_to_sse


def test_tool_end_sse_includes_field_and_value_for_save_profile_field() -> None:
    event = ToolEndEvent(
        tool="save_profile_field",
        result_summary="Saved fitness_level = intermediate",
        field="fitness_level",
        value="intermediate",
    )
    sse = _agent_event_to_sse(event, "title", "sid")
    assert sse is not None
    payload = json.loads(sse["data"])
    assert payload["field"] == "fitness_level"
    assert payload["value"] == "intermediate"


def test_tool_end_sse_no_field_for_regular_tools() -> None:
    event = ToolEndEvent(tool="search_reddit", result_summary="Found 5 posts")
    sse = _agent_event_to_sse(event, "title", "sid")
    assert sse is not None
    payload = json.loads(sse["data"])
    assert "field" not in payload
    assert "value" not in payload


@pytest.mark.asyncio
async def test_stream_response_emits_field_value_for_save_profile_field(tmp_db) -> None:
    from weles.agent.dispatch import ToolRegistry
    from weles.agent.stream import ToolEndEvent, stream_response
    from weles.tools.profile_tools import SAVE_PROFILE_FIELD_SCHEMA, save_profile_field_handler

    tool_input = {"field": "fitness_level", "value": "intermediate"}

    first_stream = MagicMock()
    first_stream.__enter__ = MagicMock(return_value=first_stream)
    first_stream.__exit__ = MagicMock(return_value=False)
    first_stream.__iter__ = MagicMock(return_value=iter([]))
    first_message = MagicMock()
    first_message.stop_reason = "tool_use"
    first_message.content = [
        ToolUseBlock(id="tu_1", name="save_profile_field", input=tool_input, type="tool_use")
    ]
    first_stream.get_final_message = MagicMock(return_value=first_message)

    text_event = RawContentBlockDeltaEvent(
        type="content_block_delta",
        index=0,
        delta=TextDelta(type="text_delta", text="Updated."),
    )
    second_stream = MagicMock()
    second_stream.__enter__ = MagicMock(return_value=second_stream)
    second_stream.__exit__ = MagicMock(return_value=False)
    stop = RawMessageStopEvent(type="message_stop")
    second_stream.__iter__ = MagicMock(return_value=iter([text_event, stop]))
    second_message = MagicMock()
    second_message.stop_reason = "end_turn"
    second_message.content = []
    second_stream.get_final_message = MagicMock(return_value=second_message)

    mock_client = MagicMock()
    mock_client.messages.stream.side_effect = [first_stream, second_stream]

    registry = ToolRegistry()
    registry.register("save_profile_field", save_profile_field_handler, SAVE_PROFILE_FIELD_SCHEMA)

    events = []
    async for event in stream_response(mock_client, [], [], [], registry):
        events.append(event)

    tool_end_events = [e for e in events if isinstance(e, ToolEndEvent)]
    assert len(tool_end_events) == 1
    assert tool_end_events[0].field == "fitness_level"
    assert tool_end_events[0].value == "intermediate"
