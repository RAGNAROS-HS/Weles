import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import anthropic
from anthropic.types import (
    RawContentBlockDeltaEvent,
    TextBlock,
    TextDelta,
    ToolUseBlock,
)
from langsmith import traceable

from weles.utils.errors import MaxToolCallsError
from weles.utils.paths import resource_path

if TYPE_CHECKING:
    from weles.agent.dispatch import ToolRegistry


@dataclass
class TextDeltaEvent:
    text: str


@dataclass
class ToolStartEvent:
    tool: str
    description: str


@dataclass
class ToolEndEvent:
    tool: str
    result_summary: str
    field: str | None = None
    value: str | None = None


@dataclass
class ToolErrorEvent:
    tool: str
    error: str


@dataclass
class DoneEvent:
    pass


AgentEvent = TextDeltaEvent | ToolStartEvent | ToolEndEvent | ToolErrorEvent | DoneEvent

_RESEARCH_TOOLS = {"search_reddit", "search_web"}
_RESEARCH_GUIDANCE: str = resource_path("src/weles/prompts/research.md").read_text(encoding="utf-8")


def _build_description(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name == "search_reddit":
        query = tool_input.get("query", "")
        subreddits = tool_input.get("subreddits", [])
        if subreddits:
            subs = ", ".join(f"r/{s}" for s in subreddits)
            return f"Searching {subs} for '{query}'…"
        return f"Searching Reddit for '{query}'…"
    if tool_name == "search_web":
        query = tool_input.get("query", "")
        return f"Searching web for '{query}'…"
    if tool_name == "add_to_history":
        item_name = tool_input.get("item_name", "item")
        return f"Saving {item_name} to history…"
    if tool_name == "save_profile_field":
        field = tool_input.get("field", "field")
        return f"Saving {field} to your profile…"
    if tool_name == "snooze_follow_up":
        return "Snoozing follow-up reminder…"
    if tool_name == "snooze_check_in":
        return "Snoozing check-in reminder…"
    if tool_name == "update_preference":
        dimension = tool_input.get("dimension", "preference")
        return f"Saving preference: {dimension}…"
    return f"Running {tool_name}…"


def _build_failure_message(failed_tools: list[str]) -> str | None:
    if not failed_tools:
        return None
    tools_str = ", ".join(failed_tools)
    return (
        f"The following tools failed: {tools_str}. "
        "Continue with available data. State in your response which sources were unavailable."
    )


@traceable(run_type="chain", name="agent_loop")
async def stream_response(
    client: anthropic.Anthropic,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    system: list[dict[str, Any]],
    registry: "ToolRegistry | None" = None,
) -> AsyncIterator[AgentEvent]:
    model = os.environ.get("WELES_MODEL", "claude-sonnet-4-6")
    max_tokens = int(os.environ.get("WELES_MAX_TOKENS", "4096"))

    current_messages = list(messages)
    research_guidance_injected = False

    while True:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": current_messages,
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
            final_message = stream.get_final_message()

        if final_message.stop_reason != "tool_use" or registry is None:
            yield DoneEvent()
            break

        tool_uses = [b for b in final_message.content if isinstance(b, ToolUseBlock)]
        tool_results = []
        failed_tools: list[str] = []

        for tool_use in tool_uses:
            description = _build_description(tool_use.name, tool_use.input)
            yield ToolStartEvent(tool=tool_use.name, description=description)
            try:
                result = await registry.adispatch(tool_use.name, tool_use.input)
                end_event = ToolEndEvent(tool=tool_use.name, result_summary=result.summary)
                if tool_use.name == "save_profile_field":
                    f = tool_use.input.get("field")
                    end_event.field = str(f) if f is not None else None
                    end_event.value = str(tool_use.input.get("value", ""))
                elif tool_use.name == "update_preference":
                    d = tool_use.input.get("dimension")
                    end_event.field = str(d) if d is not None else None
                    end_event.value = str(tool_use.input.get("value", ""))
                yield end_event
                result_content = str(result.data)
            except MaxToolCallsError:
                yield ToolErrorEvent(tool="max_tool_calls", error="Research limit reached")
                result_content = "Research limit reached. Synthesise with what you have."
            except Exception as exc:
                error_msg = str(exc)
                yield ToolErrorEvent(tool=tool_use.name, error=error_msg)
                result_content = (
                    f"Tool {tool_use.name} failed: {error_msg}. "
                    "Continue with available data; note the limitation in your response."
                )
                failed_tools.append(tool_use.name)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_content,
                }
            )

        assistant_content: list[dict[str, Any]] = []
        for block in final_message.content:
            if isinstance(block, TextBlock):
                assistant_content.append({"type": "text", "text": block.text})
            elif isinstance(block, ToolUseBlock):
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        # Build user content: tool_results FIRST (required by Anthropic API), then text blocks
        user_content: list[dict[str, Any]] = list(tool_results)

        if not research_guidance_injected and any(t.name in _RESEARCH_TOOLS for t in tool_uses):
            user_content.append({"type": "text", "text": _RESEARCH_GUIDANCE})
            research_guidance_injected = True

        failure_msg = _build_failure_message(failed_tools)
        if failure_msg:
            user_content.append({"type": "text", "text": failure_msg})

        current_messages = current_messages + [
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": user_content},
        ]
