"""Integration tests for Shopping mode: tool dispatch, history persistence, history injection."""

import contextlib
import json
from unittest.mock import MagicMock

from anthropic.types import RawContentBlockDeltaEvent, RawMessageStopEvent, TextDelta, ToolUseBlock
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "https://www.reddit.com"


def _post(title: str = "Test Post", score: int = 100, post_id: str = "p1") -> dict:
    return {
        "kind": "t3",
        "data": {
            "title": title,
            "url": f"{_BASE}/r/BuyItForLife/comments/{post_id}/",
            "score": score,
            "created_utc": 1700000000.0,
            "subreddit": "BuyItForLife",
            "selftext": "Great product",
            "id": post_id,
            "permalink": f"/r/BuyItForLife/comments/{post_id}/",
        },
    }


def _listing(*posts: dict) -> dict:
    return {"kind": "Listing", "data": {"children": list(posts)}}


def _comments() -> list:
    return [
        {"kind": "Listing", "data": {"children": []}},
        {"kind": "Listing", "data": {"children": []}},
    ]


def _make_tool_use_client(tool_name: str, tool_input: dict) -> MagicMock:
    """Claude mock: first call returns one tool_use block, second returns text + end_turn."""
    # First response: tool_use
    first_stream = MagicMock()
    first_stream.__enter__ = MagicMock(return_value=first_stream)
    first_stream.__exit__ = MagicMock(return_value=False)
    first_stream.__iter__ = MagicMock(return_value=iter([]))
    first_msg = MagicMock()
    first_msg.stop_reason = "tool_use"
    first_msg.content = [ToolUseBlock(id="tu_1", name=tool_name, input=tool_input, type="tool_use")]
    first_stream.get_final_message = MagicMock(return_value=first_msg)

    # Second response: text delta + end_turn
    text_event = RawContentBlockDeltaEvent(
        type="content_block_delta",
        index=0,
        delta=TextDelta(type="text_delta", text="Here is my analysis."),
    )
    stop_event = RawMessageStopEvent(type="message_stop")
    second_stream = MagicMock()
    second_stream.__enter__ = MagicMock(return_value=second_stream)
    second_stream.__exit__ = MagicMock(return_value=False)
    second_stream.__iter__ = MagicMock(return_value=iter([text_event, stop_event]))
    second_msg = MagicMock()
    second_msg.stop_reason = "end_turn"
    second_msg.content = []
    second_stream.get_final_message = MagicMock(return_value=second_msg)

    mock_client = MagicMock()
    mock_client.messages.stream.side_effect = [first_stream, second_stream]
    return mock_client


def _stream_events(client: TestClient, session_id: str, content: str) -> list[tuple[str, dict]]:
    events = []
    with client.stream(
        "POST", f"/sessions/{session_id}/messages", json={"content": content}
    ) as resp:
        current_event = None
        for line in resp.iter_lines():
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and current_event:
                with contextlib.suppress(json.JSONDecodeError):
                    events.append((current_event, json.loads(line.split(":", 1)[1].strip())))
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_search_reddit_dispatched_in_shopping_mode(
    client: TestClient, mocker, httpx_mock: HTTPXMock
) -> None:
    """When Claude requests search_reddit in shopping mode, the tool is dispatched
    and a tool_start + tool_end event appear in the SSE stream."""
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    httpx_mock.add_response(json=_listing(_post()))
    httpx_mock.add_response(json=_comments())

    mock_client = _make_tool_use_client(
        "search_reddit", {"query": "best waterproof jacket", "subreddits": ["malefashionadvice"]}
    )
    mocker.patch("weles.api.routers.messages.get_client", return_value=mock_client)

    session_id = client.post("/sessions").json()["id"]
    client.patch(f"/sessions/{session_id}", json={"mode": "shopping"})

    events = _stream_events(client, session_id, "best waterproof jacket under $200")

    tool_starts = [d for e, d in events if e == "tool_start"]
    tool_ends = [d for e, d in events if e == "tool_end"]
    assert any(d["tool"] == "search_reddit" for d in tool_starts)
    assert any(d["tool"] == "search_reddit" for d in tool_ends)


def test_add_to_history_dispatched_and_persisted(client: TestClient, mocker) -> None:
    """When Claude calls add_to_history in shopping mode, the item is persisted to the DB."""
    mock_client = _make_tool_use_client(
        "add_to_history",
        {
            "item_name": "Red Wing 875",
            "category": "footwear",
            "domain": "shopping",
            "status": "recommended",
        },
    )
    mocker.patch("weles.api.routers.messages.get_client", return_value=mock_client)

    session_id = client.post("/sessions").json()["id"]
    client.patch(f"/sessions/{session_id}", json={"mode": "shopping"})

    _stream_events(client, session_id, "what boots should I get")

    history = client.get("/history?domain=shopping").json()["items"]
    assert any(item["item_name"] == "Red Wing 875" for item in history)


def test_history_context_injected_for_shopping_domain(client: TestClient, mock_claude) -> None:
    """When shopping history exists, the history context block is injected into the user turn
    passed to Claude."""
    from weles.tools.history_tools import add_to_history_handler

    add_to_history_handler(
        {
            "item_name": "Danner Mountain Light",
            "category": "footwear",
            "domain": "shopping",
            "status": "recommended",
        }
    )

    session_id = client.post("/sessions").json()["id"]
    client.patch(f"/sessions/{session_id}", json={"mode": "shopping"})

    with client.stream(
        "POST", f"/sessions/{session_id}/messages", json={"content": "hiking boots"}
    ) as resp:
        for _ in resp.iter_lines():
            pass  # consume stream

    call_messages = mock_claude.messages.stream.call_args[1]["messages"]
    last_user_content = call_messages[-1]["content"]
    assert "Danner Mountain Light" in last_user_content
