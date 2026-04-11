import pytest

from weles.agent.stream import DoneEvent, TextDeltaEvent, stream_response


@pytest.mark.asyncio
async def test_stream_response_yields_text_delta(mock_claude):
    events = []
    async for event in stream_response(mock_claude, messages=[], tools=[], system=[]):
        events.append(event)
    text_events = [e for e in events if isinstance(e, TextDeltaEvent)]
    assert len(text_events) == 1
    assert text_events[0].text == "Test."


@pytest.mark.asyncio
async def test_stream_response_yields_done_event_last(mock_claude):
    events = []
    async for event in stream_response(mock_claude, messages=[], tools=[], system=[]):
        events.append(event)
    assert isinstance(events[-1], DoneEvent)
