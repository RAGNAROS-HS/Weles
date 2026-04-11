import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import anthropic
from anthropic.types import RawContentBlockDeltaEvent, RawMessageStopEvent, TextDelta


@dataclass
class TextDeltaEvent:
    text: str


@dataclass
class ToolStartEvent:
    tool: str
    tool_use_id: str


@dataclass
class ToolEndEvent:
    tool: str
    result: str


@dataclass
class ToolErrorEvent:
    tool: str
    error: str


@dataclass
class DoneEvent:
    pass


AgentEvent = TextDeltaEvent | ToolStartEvent | ToolEndEvent | ToolErrorEvent | DoneEvent


async def stream_response(
    client: anthropic.Anthropic,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    system: list[dict[str, Any]],
) -> AsyncIterator[AgentEvent]:
    model = os.environ.get("WELES_MODEL", "claude-sonnet-4-6")
    max_tokens = int(os.environ.get("WELES_MAX_TOKENS", "4096"))

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if isinstance(event, RawContentBlockDeltaEvent) and isinstance(
                event.delta, TextDelta
            ):
                yield TextDeltaEvent(text=event.delta.text)
            elif isinstance(event, RawMessageStopEvent):
                yield DoneEvent()
