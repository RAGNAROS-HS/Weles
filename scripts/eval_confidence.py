#!/usr/bin/env python3
"""
Confidence calibration evaluation script.
Runs 5 queries targeting different signal-strength scenarios against live Claude
and prints results for manual review of confidence label usage.

Requires: ANTHROPIC_API_KEY set in env. TAVILY_API_KEY optional.
Not a CI test — run manually for qualitative review.

Usage:
    uv run python scripts/eval_confidence.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure src/ is on the path when run from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

QUERIES = [
    # Expected: [thin data] — very niche, little community discussion
    ("shopping", "What do people think of the Bellroy Venture Ready Pack backpack?"),
    # Expected: [strong consensus] — popular, well-documented product
    ("shopping", "What do long-term owners say about the Benchmade Bugout knife?"),
    # Expected: [divided community] — genuine disagreement in running community
    ("fitness", "Is running in Hokas better or worse than minimalist shoes for injury prevention?"),
    # Expected: [thin data] or data age flag — product is old/discontinued
    ("shopping", "What do people say about the Vibram FiveFingers Bikila?"),
    # Expected: [thin data] — niche category with sparse community data
    ("diet", "What supplements do people recommend for improving sleep quality in elite athletes?"),
]

_LABELS = ["[strong consensus]", "[divided community]", "[thin data]"]


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

    print(f"\n{'=' * 70}")
    print(f"Mode: {mode}")
    print(f"Query: {query}")
    print("=" * 70)

    full_text: list[str] = []

    async for event in stream_response(
        client, messages, registry.get_tool_schemas(), system, registry
    ):
        if isinstance(event, TextDeltaEvent):
            print(event.text, end="", flush=True)
            full_text.append(event.text)
        elif isinstance(event, ToolStartEvent):
            print(f"\n[TOOL: {event.description}]", flush=True)
        elif isinstance(event, ToolEndEvent):
            print(f"[TOOL DONE: {event.result_summary}]", flush=True)
        elif isinstance(event, ToolErrorEvent):
            print(f"[TOOL ERROR: {event.tool} — {event.error}]", flush=True)
        elif isinstance(event, DoneEvent):
            print("\n[DONE]", flush=True)

    response = "".join(full_text)
    found = [label for label in _LABELS if label in response]
    if found:
        print(f"\n  ✓ Confidence label used: {found[0]}")
    else:
        print("\n  ✗ WARNING: No confidence label found in response")


async def main() -> None:
    print("Confidence calibration eval — 5 scenarios")
    print("Labels to look for: [strong consensus] | [divided community] | [thin data]")
    for mode, query in QUERIES:
        await run_query(mode, query)
    print("\n\nDone. Review each response for correct label placement and reasoning quality.")


if __name__ == "__main__":
    asyncio.run(main())
