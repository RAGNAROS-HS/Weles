#!/usr/bin/env python3
"""
Manual eval script for research synthesis quality.
Runs 5 representative queries against live Claude and prints results.

Requires: ANTHROPIC_API_KEY set. TAVILY_API_KEY optional (enables web search).
Not a CI test — run manually for qualitative review.

Usage:
    uv run python scripts/eval_research.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure src/ is on the path when run from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

QUERIES = [
    ("shopping", "What's the best budget mechanical keyboard for daily use?"),
    ("shopping", "Recommend a durable cast iron pan for a beginner cook"),
    ("fitness", "What running shoes do long-distance runners recommend?"),
    ("diet", "What do people say about intermittent fasting for weight loss?"),
    ("lifestyle", "What air purifier is most recommended by allergy sufferers?"),
]


async def run_query(mode: str, query: str) -> None:
    from weles.agent.client import get_client
    from weles.agent.dispatch import ToolRegistry
    from weles.agent.prompts import build_system_prompt
    from weles.agent.stream import (
        DoneEvent,
        TextDeltaEvent,
        ToolEndEvent,
        ToolErrorEvent,
        ToolStartEvent,
        stream_response,
    )
    from weles.tools.reddit import SEARCH_REDDIT_SCHEMA, search_reddit_handler

    client = get_client()
    system = build_system_prompt(mode)
    registry = ToolRegistry(max_calls=6)
    registry.register("search_reddit", search_reddit_handler, SEARCH_REDDIT_SCHEMA)

    if os.getenv("TAVILY_API_KEY"):
        from weles.tools.web import SEARCH_WEB_SCHEMA, search_web_handler

        registry.register("search_web", search_web_handler, SEARCH_WEB_SCHEMA)

    messages = [{"role": "user", "content": query}]

    print(f"\n{'=' * 60}")
    print(f"Mode: {mode}  |  Query: {query}")
    print("=" * 60)

    async for event in stream_response(
        client, messages, registry.get_tool_schemas(), system, registry
    ):
        if isinstance(event, TextDeltaEvent):
            print(event.text, end="", flush=True)
        elif isinstance(event, ToolStartEvent):
            print(f"\n[TOOL: {event.description}]", flush=True)
        elif isinstance(event, ToolEndEvent):
            print(f"[TOOL DONE: {event.result_summary}]", flush=True)
        elif isinstance(event, ToolErrorEvent):
            print(f"[TOOL ERROR: {event.tool} — {event.error}]", flush=True)
        elif isinstance(event, DoneEvent):
            print("\n[DONE]", flush=True)


async def main() -> None:
    for mode, query in QUERIES:
        await run_query(mode, query)


if __name__ == "__main__":
    asyncio.run(main())
